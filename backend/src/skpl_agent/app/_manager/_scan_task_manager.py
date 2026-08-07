"""
Scan Task Manager — Manages asynchronous anatomy scan tasks.

Provides a queue-based system for handling scan requests:
- Scans are queued and processed asynchronously
- Supports progress tracking via callbacks
- Handles concurrent scan requests with deduplication
- Integrates with the file watch manager for incremental scans

This enables the "deferred scan" pattern where API requests return
immediately with a task_id, and the frontend polls for progress.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from skpl_agent.context.anatomy_scanner import AnatomyScanner, ScanMode, ScanOptions, ScanResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


class ScanTaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScanTask:
    """A single scan task."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    root_path: str = ""
    mode: ScanMode = ScanMode.FULL
    changed_files: list[str] = field(default_factory=list)
    status: ScanTaskStatus = ScanTaskStatus.QUEUED
    progress: int = 0
    progress_total: int = 0
    current_file: str = ""
    result: ScanResult | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    on_progress: Optional[Callable[[str, int, int, str], None]] = None


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class ScanTaskManager:
    """Manages asynchronous anatomy scan tasks.

    Usage:
        mgr = ScanTaskManager(max_concurrent=2)
        task_id = await mgr.submit("/path/to/project")
        status = mgr.get_status(task_id)
        # ... poll for completion ...
        result = mgr.get_result(task_id)
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        default_max_workers: int = 4,
    ):
        self.max_concurrent = max_concurrent
        self.default_max_workers = default_max_workers

        # State
        self._tasks: dict[str, ScanTask] = {}
        self._queue: asyncio.Queue[ScanTask] = asyncio.Queue()
        self._running_tasks: set[str] = set()
        self._worker_task: asyncio.Task | None = None
        self._running: bool = False

    # -- Lifecycle --

    async def start(self) -> None:
        """Start the scan task manager."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Scan task manager started (max_concurrent=%d)", self.max_concurrent)

    async def stop(self) -> None:
        """Stop the scan task manager."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        logger.info("Scan task manager stopped")

    # -- Task Submission --

    async def submit(
        self,
        root_path: str | Path,
        mode: ScanMode = ScanMode.FULL,
        changed_files: list[str] | None = None,
        on_progress: Optional[Callable[[str, int, int, str], None]] = None,
    ) -> str:
        """Submit a scan task. Returns task_id for polling."""
        # Deduplicate: if a full scan is already queued for the same path, skip
        for task in self._tasks.values():
            if (
                task.root_path == str(root_path)
                and task.mode == mode
                and task.status in (ScanTaskStatus.QUEUED, ScanTaskStatus.RUNNING)
            ):
                logger.info("Duplicate scan task skipped for %s", root_path)
                return task.task_id

        task = ScanTask(
            root_path=str(root_path),
            mode=mode,
            changed_files=changed_files or [],
            on_progress=on_progress,
        )

        self._tasks[task.task_id] = task
        await self._queue.put(task)

        logger.info(
            "Scan task submitted: %s (mode=%s, path=%s)",
            task.task_id,
            mode.value,
            root_path,
        )
        return task.task_id

    # -- Status Queries --

    def get_status(self, task_id: str) -> dict | None:
        """Get the status of a scan task."""
        task = self._tasks.get(task_id)
        if task is None:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "progress_total": task.progress_total,
            "current_file": task.current_file,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    def get_result(self, task_id: str) -> ScanResult | None:
        """Get the result of a completed scan task."""
        task = self._tasks.get(task_id)
        if task is None or task.status != ScanTaskStatus.COMPLETED:
            return None
        return task.result

    def get_error(self, task_id: str) -> str | None:
        """Get the error of a failed scan task."""
        task = self._tasks.get(task_id)
        return task.error if task else None

    def list_tasks(self, status: ScanTaskStatus | None = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]

        return [
            {
                "task_id": t.task_id,
                "root_path": t.root_path,
                "mode": t.mode.value,
                "status": t.status.value,
                "progress": t.progress,
                "progress_total": t.progress_total,
                "created_at": t.created_at.isoformat(),
            }
            for t in sorted(tasks, key=lambda t: t.created_at, reverse=True)
        ]

    # -- Control --

    def cancel(self, task_id: str) -> bool:
        """Cancel a queued or running scan task."""
        task = self._tasks.get(task_id)
        if task is None:
            return False

        if task.status in (ScanTaskStatus.QUEUED, ScanTaskStatus.RUNNING):
            task.status = ScanTaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            self._running_tasks.discard(task_id)
            logger.info("Scan task cancelled: %s", task_id)
            return True

        return False

    def cleanup_old(self, max_age_seconds: float = 3600) -> int:
        """Remove completed tasks older than max_age_seconds."""
        now = datetime.now(timezone.utc)
        removed = 0
        for task_id in list(self._tasks.keys()):
            task = self._tasks[task_id]
            if task.status in (ScanTaskStatus.COMPLETED, ScanTaskStatus.FAILED, ScanTaskStatus.CANCELLED):
                if task.completed_at and (now - task.completed_at).total_seconds() > max_age_seconds:
                    del self._tasks[task_id]
                    removed += 1
        return removed

    # -- Worker Loop --

    async def _worker_loop(self) -> None:
        """Main worker loop that processes scan tasks."""
        while self._running:
            try:
                # Wait for available slot
                while len(self._running_tasks) >= self.max_concurrent:
                    await asyncio.sleep(0.1)

                task = await self._queue.get()
                if task.status == ScanTaskStatus.CANCELLED:
                    continue

                self._running_tasks.add(task.task_id)
                asyncio.create_task(self._process_task(task))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scan worker error: %s", e)

    async def _process_task(self, task: ScanTask) -> None:
        """Process a single scan task."""
        task.status = ScanTaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)

        try:
            # Progress callback
            def _progress(current: int, total: int, file_path: str):
                task.progress = current
                task.progress_total = total
                task.current_file = file_path
                if task.on_progress:
                    try:
                        task.on_progress(task.task_id, current, total, file_path)
                    except Exception:
                        pass

            options = ScanOptions(
                mode=task.mode,
                root_path=Path(task.root_path),
                changed_files=task.changed_files,
                max_workers=self.default_max_workers,
                on_progress=_progress,
            )

            scanner = AnatomyScanner(options)
            try:
                task.result = await scanner.scan()
            finally:
                scanner.close()

            task.status = ScanTaskStatus.COMPLETED
            task.progress = task.progress_total  # 100%

            logger.info(
                "Scan task completed: %s (%d files, %d symbols, %.1fs)",
                task.task_id,
                task.result.total_files_scanned,
                task.result.total_symbols_extracted,
                task.result.duration_seconds,
            )

        except Exception as e:
            task.status = ScanTaskStatus.FAILED
            task.error = str(e)
            logger.error("Scan task failed: %s — %s", task.task_id, e)

        finally:
            task.completed_at = datetime.now(timezone.utc)
            self._running_tasks.discard(task.task_id)