"""Desktop Scheduler — task scheduling and load balancing across nodes.

Provides:
- Priority-based action queue
- Load-balanced node selection
- Action lifecycle tracking
- Timeout and retry management
- Concurrent action limits per node
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from skpl_agent.app._service.node_registry import NodeRegistry, RegisteredNode

logger = logging.getLogger(__name__)


class ActionPriority(int, Enum):
    """Priority levels for scheduled actions."""
    LOW = 0
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class ScheduleStatus(str, Enum):
    """Status of a scheduled action."""
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    RETRYING = "retrying"


@dataclass
class ScheduledAction:
    """A scheduled desktop action with lifecycle tracking.

    Attributes:
        action_id: Unique action identifier.
        tenant_id: Owning tenant.
        action_type: Type of action (click, type, screenshot, etc.).
        params: Action parameters.
        priority: Scheduling priority.
        status: Current status.
        node_id: Assigned node (set after dispatch).
        result: Action result data.
        error: Error message if failed.
        max_retries: Maximum retry attempts on failure.
        retry_count: Current retry count.
        timeout: Action timeout in seconds.
        created_at: When the action was created.
        dispatched_at: When the action was dispatched to a node.
        completed_at: When the action completed.
        on_complete: Optional callback for completion.
    """

    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tenant_id: str = "default"
    action_type: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    priority: ActionPriority = ActionPriority.NORMAL
    status: ScheduleStatus = ScheduleStatus.QUEUED

    node_id: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    max_retries: int = 3
    retry_count: int = 0
    timeout: float = 30.0

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    dispatched_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    on_complete: Optional[Callable] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "tenant_id": self.tenant_id,
            "action_type": self.action_type,
            "priority": self.priority.name,
            "status": self.status,
            "node_id": self.node_id,
            "error": self.error,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @property
    def is_terminal(self) -> bool:
        """Check if the action has reached a terminal state."""
        return self.status in (
            ScheduleStatus.COMPLETED,
            ScheduleStatus.FAILED,
            ScheduleStatus.CANCELLED,
            ScheduleStatus.TIMED_OUT,
        )

    @property
    def can_retry(self) -> bool:
        """Check if the action can be retried."""
        return (
            self.status in (ScheduleStatus.FAILED, ScheduleStatus.TIMED_OUT)
            and self.retry_count < self.max_retries
        )


class DesktopScheduler:
    """Schedules and dispatches desktop actions across registered nodes.

    Features:
    - Priority queue for action scheduling
    - Load-balanced node selection via NodeRegistry
    - Automatic retry with exponential backoff
    - Concurrent action limits per node
    - Timeout enforcement
    - Action lifecycle callbacks

    Usage:
        >>> registry = NodeRegistry()
        >>> scheduler = DesktopScheduler(
        ...     registry=registry,
        ...     dispatch_callback=send_to_node,
        ... )
        >>> action = await scheduler.schedule(
        ...     action_type="click",
        ...     params={"x": 100, "y": 200},
        ... )
        >>> await scheduler.start()
    """

    def __init__(
        self,
        registry: NodeRegistry,
        dispatch_callback: Callable[[ScheduledAction, RegisteredNode], Any],
        max_concurrent_per_node: int = 3,
        default_timeout: float = 30.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._registry = registry
        self._dispatch_callback = dispatch_callback
        self._max_concurrent_per_node = max_concurrent_per_node
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

        self._queue: list[ScheduledAction] = []
        self._actions: dict[str, ScheduledAction] = {}
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

    # ── Scheduling ───────────────────────────────────────────────────────

    async def schedule(
        self,
        action_type: str,
        params: dict[str, Any],
        tenant_id: str = "default",
        priority: ActionPriority = ActionPriority.NORMAL,
        timeout: float | None = None,
        on_complete: Callable | None = None,
    ) -> ScheduledAction:
        """Schedule a new action for execution.

        Args:
            action_type: Type of action (click, type, screenshot, etc.).
            params: Action parameters.
            tenant_id: Tenant for multi-tenant isolation.
            priority: Scheduling priority.
            timeout: Action timeout in seconds.
            on_complete: Optional callback when action completes.

        Returns:
            The scheduled action (status=QUEUED).
        """
        action = ScheduledAction(
            tenant_id=tenant_id,
            action_type=action_type,
            params=params,
            priority=priority,
            timeout=timeout or self._default_timeout,
            max_retries=self._max_retries,
            on_complete=on_complete,
        )

        self._actions[action.action_id] = action
        self._queue.append(action)
        self._queue.sort(key=lambda a: a.priority, reverse=True)

        logger.debug(
            "Action scheduled: %s type=%s priority=%s",
            action.action_id, action_type, priority.name,
        )

        return action

    async def cancel(self, action_id: str) -> bool:
        """Cancel a scheduled or running action.

        Args:
            action_id: Action to cancel.

        Returns:
            True if cancelled, False if not found or already terminal.
        """
        action = self._actions.get(action_id)
        if action is None or action.is_terminal:
            return False

        action.status = ScheduleStatus.CANCELLED
        action.completed_at = datetime.now(timezone.utc)

        # Remove from queue if still queued
        self._queue = [a for a in self._queue if a.action_id != action_id]

        if action.on_complete:
            try:
                result = action.on_complete(action)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("on_complete callback error: %s", e)

        return True

    async def get_action(self, action_id: str) -> Optional[ScheduledAction]:
        """Get an action by ID."""
        return self._actions.get(action_id)

    async def list_actions(
        self,
        tenant_id: str | None = None,
        status: ScheduleStatus | None = None,
    ) -> list[ScheduledAction]:
        """List actions with optional filters."""
        actions = list(self._actions.values())
        if tenant_id:
            actions = [a for a in actions if a.tenant_id == tenant_id]
        if status:
            actions = [a for a in actions if a.status == status]
        return sorted(actions, key=lambda a: a.created_at, reverse=True)

    # ── Dispatch Loop ────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the dispatch loop."""
        if self._running:
            return
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("Desktop scheduler started")

    async def stop(self) -> None:
        """Stop the dispatch loop."""
        self._running = False
        if self._dispatch_task and not self._dispatch_task.done():
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        self._dispatch_task = None
        logger.info("Desktop scheduler stopped")

    async def _dispatch_loop(self) -> None:
        """Main dispatch loop — processes the queue continuously."""
        while self._running:
            try:
                dispatched = await self._dispatch_next()
                if not dispatched:
                    await asyncio.sleep(0.5)  # No work, brief pause
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Dispatch loop error: %s", e)
                await asyncio.sleep(1.0)

    async def _dispatch_next(self) -> bool:
        """Try to dispatch the next queued action.

        Returns:
            True if an action was dispatched, False otherwise.
        """
        if not self._queue:
            return False

        # Find a node for the highest priority action
        for action in self._queue:
            node = self._registry.select_best_node(
                tenant_id=action.tenant_id,
            )

            if node is None:
                continue

            # Check node concurrency limit
            active_count = sum(
                1 for a in self._actions.values()
                if a.node_id == node.node_id
                and a.status == ScheduleStatus.RUNNING
            )
            if active_count >= self._max_concurrent_per_node:
                continue

            # Dispatch!
            action.node_id = node.node_id
            action.status = ScheduleStatus.DISPATCHED
            action.dispatched_at = datetime.now(timezone.utc)

            self._queue.remove(action)

            logger.info(
                "Action dispatched: %s -> node %s (%s)",
                action.action_id, node.node_name, action.action_type,
            )

            try:
                result = self._dispatch_callback(action, node)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(
                    "Dispatch callback failed for %s: %s",
                    action.action_id, e,
                )
                await self._handle_action_failure(action, str(e))

            return True

        return False

    # ── Action Lifecycle ─────────────────────────────────────────────────

    async def on_action_started(self, action_id: str) -> None:
        """Mark an action as running."""
        action = self._actions.get(action_id)
        if action:
            action.status = ScheduleStatus.RUNNING

    async def on_action_completed(
        self, action_id: str, result: dict[str, Any]
    ) -> None:
        """Mark an action as completed successfully."""
        action = self._actions.get(action_id)
        if action:
            action.status = ScheduleStatus.COMPLETED
            action.result = result
            action.completed_at = datetime.now(timezone.utc)
            logger.info("Action completed: %s", action_id)
            await self._fire_completion(action)

    async def on_action_failed(
        self, action_id: str, error: str
    ) -> None:
        """Mark an action as failed and attempt retry."""
        await self._handle_action_failure(action_id, error)

    async def _handle_action_failure(
        self, action_id: str, error: str
    ) -> None:
        """Handle action failure with automatic retry."""
        action = self._actions.get(action_id)
        if action is None:
            return

        action.error = error

        if action.can_retry:
            action.retry_count += 1
            action.status = ScheduleStatus.RETRYING
            action.node_id = ""

            # Exponential backoff
            delay = self._retry_base_delay * (2 ** (action.retry_count - 1))
            logger.warning(
                "Action %s failed, retrying in %.1fs (attempt %d/%d): %s",
                action_id, delay, action.retry_count, action.max_retries, error,
            )

            await asyncio.sleep(delay)
            action.status = ScheduleStatus.QUEUED
            self._queue.append(action)
            self._queue.sort(key=lambda a: a.priority, reverse=True)
        else:
            action.status = ScheduleStatus.FAILED
            action.completed_at = datetime.now(timezone.utc)
            logger.error(
                "Action %s failed permanently (retries exhausted): %s",
                action_id, error,
            )
            await self._fire_completion(action)

    async def on_action_timed_out(self, action_id: str) -> None:
        """Mark an action as timed out."""
        action = self._actions.get(action_id)
        if action:
            action.error = "Action timed out"
            logger.warning("Action timed out: %s", action_id)
            await self._handle_action_failure(action_id, "Action timed out")

    async def _fire_completion(self, action: ScheduledAction) -> None:
        """Fire the completion callback if set."""
        if action.on_complete:
            try:
                result = action.on_complete(action)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("on_complete callback error: %s", e)

    # ── Stats ────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        actions = list(self._actions.values())
        return {
            "queue_size": len(self._queue),
            "total_actions": len(actions),
            "by_status": {
                status: sum(1 for a in actions if a.status == status)
                for status in ScheduleStatus
            },
            "avg_wait_time_ms": self._avg_wait_time(actions),
        }

    @staticmethod
    def _avg_wait_time(actions: list[ScheduledAction]) -> float:
        """Calculate average wait time for dispatched actions."""
        completed = [
            a for a in actions
            if a.dispatched_at and a.completed_at
        ]
        if not completed:
            return 0.0
        total = sum(
            (a.completed_at - a.created_at).total_seconds() * 1000
            for a in completed
        )
        return total / len(completed)