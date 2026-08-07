"""Desktop Node Registry — tracks and monitors connected desktop nodes.

Provides:
- Node registration and lifecycle management
- Heartbeat monitoring with automatic timeout detection
- Stale node cleanup
- Node capability-based selection
- Multi-tenant node isolation
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegisteredNode:
    """A registered desktop node with runtime state.

    Attributes:
        node_id: Unique node identifier.
        node_name: Human-readable node name.
        tenant_id: Owning tenant for multi-tenant isolation.
        session_id: Current WebSocket session ID.
        status: Node status (connecting/online/idle/busy/offline).
        os_name: Operating system name.
        os_version: Operating system version.
        python_version: Python version on the node.
        screen_width: Screen width in pixels.
        screen_height: Screen height in pixels.
        cpu_count: Number of logical CPU cores.
        total_memory_mb: Total RAM in megabytes.
        capabilities: List of supported capabilities.
        installed_apps: List of installed applications.
        cpu_percent: Current CPU usage percentage.
        memory_percent: Current memory usage percentage.
        disk_percent: Current disk usage percentage.
        active_actions: Number of currently executing actions.
        registered_at: When the node first registered.
        last_seen: When the node was last seen (heartbeat/activity).
        metadata: Arbitrary key-value metadata.
    """

    node_id: str
    node_name: str = ""
    tenant_id: str = "default"
    session_id: str = ""
    status: str = "connecting"

    # System info
    os_name: str = ""
    os_version: str = ""
    python_version: str = ""
    screen_width: int = 0
    screen_height: int = 0
    cpu_count: int = 0
    total_memory_mb: int = 0

    # Capabilities
    capabilities: list[str] = field(default_factory=list)
    installed_apps: list[str] = field(default_factory=list)

    # Dynamic metrics
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    active_actions: int = 0

    # Timestamps
    registered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_online(self) -> bool:
        return self.status in ("online", "idle", "busy")

    @property
    def is_available(self) -> bool:
        """Node is available to accept new actions."""
        return self.is_online and self.active_actions < 5

    @property
    def load_score(self) -> float:
        """Composite load score (lower = less loaded)."""
        return (
            self.cpu_percent * 0.4
            + self.memory_percent * 0.3
            + self.active_actions * 10 * 0.3
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "cpu_count": self.cpu_count,
            "total_memory_mb": self.total_memory_mb,
            "capabilities": self.capabilities,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "active_actions": self.active_actions,
            "registered_at": self.registered_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "is_available": self.is_available,
        }


class NodeRegistry:
    """Registry for tracking and monitoring desktop nodes.

    Features:
    - Thread-safe node registration and lookup
    - Automatic stale node detection and cleanup
    - Capability-based node selection
    - Multi-tenant isolation
    - Event callbacks for node lifecycle events

    Usage:
        >>> registry = NodeRegistry(heartbeat_timeout=60)
        >>> await registry.register(node)
        >>> node = await registry.select_best_node(tenant_id="default")
        >>> await registry.heartbeat(node_id)
        >>> await registry.start_cleanup_task()
    """

    def __init__(
        self,
        heartbeat_timeout: float = 60.0,
        cleanup_interval: float = 30.0,
    ) -> None:
        self._heartbeat_timeout = heartbeat_timeout
        self._cleanup_interval = cleanup_interval
        self._nodes: dict[str, RegisteredNode] = {}
        self._session_to_node: dict[str, str] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks
        self._on_register: list[callable] = []
        self._on_unregister: list[callable] = []
        self._on_timeout: list[callable] = []

    # ── Registration ─────────────────────────────────────────────────────

    def on_register(self, callback):
        """Register a callback for node registration events."""
        self._on_register.append(callback)

    def on_unregister(self, callback):
        """Register a callback for node unregistration events."""
        self._on_unregister.append(callback)

    def on_timeout(self, callback):
        """Register a callback for node timeout events."""
        self._on_timeout.append(callback)

    async def register(self, node: RegisteredNode) -> None:
        """Register a new node or update an existing one."""
        is_new = node.node_id not in self._nodes
        self._nodes[node.node_id] = node
        if node.session_id:
            self._session_to_node[node.session_id] = node.node_id

        if is_new:
            logger.info(
                "Node registered: %s (%s) [%s]",
                node.node_name, node.node_id, node.os_name,
            )
            for cb in self._on_register:
                try:
                    result = cb(node)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error("on_register callback error: %s", e)

    async def unregister(self, node_id: str) -> Optional[RegisteredNode]:
        """Remove a node from the registry."""
        node = self._nodes.pop(node_id, None)
        if node:
            self._session_to_node.pop(node.session_id, None)
            logger.info("Node unregistered: %s (%s)", node.node_name, node_id)
            for cb in self._on_unregister:
                try:
                    result = cb(node)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error("on_unregister callback error: %s", e)
        return node

    def unregister_by_session(self, session_id: str) -> Optional[RegisteredNode]:
        """Remove a node by its WebSocket session ID."""
        node_id = self._session_to_node.pop(session_id, None)
        if node_id:
            return self._nodes.pop(node_id, None)
        return None

    # ── Lookup ───────────────────────────────────────────────────────────

    def get(self, node_id: str) -> Optional[RegisteredNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_by_session(self, session_id: str) -> Optional[RegisteredNode]:
        """Get a node by its WebSocket session ID."""
        node_id = self._session_to_node.get(session_id)
        if node_id:
            return self._nodes.get(node_id)
        return None

    def list_all(self) -> list[RegisteredNode]:
        """List all registered nodes."""
        return list(self._nodes.values())

    def list_by_tenant(self, tenant_id: str) -> list[RegisteredNode]:
        """List nodes belonging to a specific tenant."""
        return [
            n for n in self._nodes.values()
            if n.tenant_id == tenant_id
        ]

    def list_online(self) -> list[RegisteredNode]:
        """List all online nodes."""
        return [n for n in self._nodes.values() if n.is_online]

    def list_available(self) -> list[RegisteredNode]:
        """List all nodes available for new actions."""
        return [n for n in self._nodes.values() if n.is_available]

    def count(self) -> int:
        """Total number of registered nodes."""
        return len(self._nodes)

    def count_online(self) -> int:
        """Number of online nodes."""
        return sum(1 for n in self._nodes.values() if n.is_online)

    # ── Heartbeat ────────────────────────────────────────────────────────

    async def heartbeat(
        self,
        node_id: str,
        metrics: dict[str, Any] | None = None,
    ) -> bool:
        """Record a heartbeat from a node.

        Updates the last_seen timestamp and optionally dynamic metrics.

        Returns:
            True if the node exists, False otherwise.
        """
        node = self._nodes.get(node_id)
        if node is None:
            return False

        node.last_seen = datetime.now(timezone.utc)

        if node.status == "connecting":
            node.status = "online"

        if metrics:
            node.cpu_percent = metrics.get("cpu_percent", node.cpu_percent)
            node.memory_percent = metrics.get("memory_percent", node.memory_percent)
            node.disk_percent = metrics.get("disk_percent", node.disk_percent)
            node.active_actions = metrics.get("active_actions", node.active_actions)

        return True

    async def update_node_info(
        self,
        node_id: str,
        info: dict[str, Any],
    ) -> Optional[RegisteredNode]:
        """Update node system information."""
        node = self._nodes.get(node_id)
        if node is None:
            return None

        for key in (
            "node_name", "os_name", "os_version", "python_version",
            "screen_width", "screen_height", "cpu_count", "total_memory_mb",
            "capabilities", "installed_apps",
        ):
            if key in info:
                setattr(node, key, info[key])

        node.last_seen = datetime.now(timezone.utc)
        return node

    # ── Node Selection ───────────────────────────────────────────────────

    def select_best_node(
        self,
        tenant_id: str = "default",
        required_capabilities: list[str] | None = None,
    ) -> Optional[RegisteredNode]:
        """Select the best available node for a task.

        Selection criteria (in order):
        1. Tenant matches
        2. Node is available (online + not overloaded)
        3. Has required capabilities (if specified)
        4. Lowest load score (CPU + memory + active actions)

        Args:
            tenant_id: Tenant to select from.
            required_capabilities: Capabilities the node must have.

        Returns:
            The best matching node, or None if no suitable node found.
        """
        candidates = [
            n for n in self._nodes.values()
            if n.tenant_id == tenant_id and n.is_available
        ]

        if required_capabilities:
            candidates = [
                n for n in candidates
                if all(cap in n.capabilities for cap in required_capabilities)
            ]

        if not candidates:
            return None

        # Select node with lowest load
        return min(candidates, key=lambda n: n.load_score)

    def select_node_for_app(
        self,
        app_name: str,
        tenant_id: str = "default",
    ) -> Optional[RegisteredNode]:
        """Select a node that has a specific application installed.

        Args:
            app_name: Application name to match.
            tenant_id: Tenant to select from.

        Returns:
            Matching node or None.
        """
        candidates = [
            n for n in self._nodes.values()
            if n.tenant_id == tenant_id
            and n.is_available
            and any(app_name.lower() in a.lower() for a in n.installed_apps)
        ]

        if not candidates:
            return None

        return min(candidates, key=lambda n: n.load_score)

    # ── Cleanup ──────────────────────────────────────────────────────────

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            "Node registry cleanup started (timeout=%.0fs, interval=%.0fs)",
            self._heartbeat_timeout, self._cleanup_interval,
        )

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Periodically check for stale nodes."""
        while self._running:
            try:
                await self._cleanup_stale_nodes()
            except Exception as e:
                logger.error("Cleanup error: %s", e)
            await asyncio.sleep(self._cleanup_interval)

    async def _cleanup_stale_nodes(self) -> None:
        """Find and remove nodes that haven't sent heartbeats."""
        now = datetime.now(timezone.utc)
        stale_ids: list[str] = []

        for node_id, node in self._nodes.items():
            elapsed = (now - node.last_seen).total_seconds()
            if elapsed > self._heartbeat_timeout:
                stale_ids.append(node_id)
                logger.warning(
                    "Node %s (%s) timed out after %.0fs",
                    node.node_name, node_id, elapsed,
                )
                for cb in self._on_timeout:
                    try:
                        result = cb(node)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error("on_timeout callback error: %s", e)

        for node_id in stale_ids:
            await self.unregister(node_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        nodes = list(self._nodes.values())
        online = [n for n in nodes if n.is_online]
        return {
            "total_nodes": len(nodes),
            "online_nodes": len(online),
            "offline_nodes": len(nodes) - len(online),
            "available_nodes": sum(1 for n in nodes if n.is_available),
            "by_tenant": {
                tenant: len([n for n in nodes if n.tenant_id == tenant])
                for tenant in set(n.tenant_id for n in nodes)
            },
            "by_os": {
                os_name: len([n for n in nodes if n.os_name == os_name])
                for os_name in set(n.os_name for n in nodes)
            },
        }