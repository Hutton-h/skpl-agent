"""
File Watch Manager — Monitors project files for changes.

Uses watchdog (when available) to detect file changes and trigger
incremental anatomy scans. Implements a 200ms debounce to prevent
event storms from rapid file changes.

Fallback: polling-based change detection when watchdog is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional, Set

logger = logging.getLogger(__name__)

# Try to import watchdog
_HAS_WATCHDOG = False
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _HAS_WATCHDOG = True
except ImportError:
    pass

# Default debounce period (seconds)
DEFAULT_DEBOUNCE_SECONDS = 0.2


class FileWatchManager:
    """Watches project directories for file changes.

    When changes are detected, triggers incremental anatomy scans
    via the provided callback.

    Usage:
        mgr = FileWatchManager(
            watch_path="/path/to/project",
            on_change=handle_files_changed,
        )
        await mgr.start()
        # ... later ...
        await mgr.stop()
    """

    def __init__(
        self,
        watch_path: str | Path,
        on_change: Callable[[list[str]], None],
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        ignore_dirs: set[str] | None = None,
        scan_extensions: set[str] | None = None,
        use_polling: bool = False,
        poll_interval: float = 5.0,
    ):
        self.watch_path = Path(watch_path)
        self._on_change = on_change
        self._debounce_seconds = debounce_seconds
        self._ignore_dirs = ignore_dirs or {
            ".git", ".svn", "node_modules", "__pycache__",
            ".mypy_cache", ".pytest_cache", "venv", ".venv",
            "dist", "build", ".idea", ".vscode", ".skpl",
        }
        self._scan_extensions = scan_extensions
        self._use_polling = use_polling or not _HAS_WATCHDOG
        self._poll_interval = poll_interval

        # State
        self._observer: Optional["Observer"] = None
        self._running: bool = False
        self._pending_changes: Set[str] = set()
        self._debounce_task: asyncio.Task | None = None
        self._poll_task: asyncio.Task | None = None
        self._file_mtimes: dict[str, float] = {}

    # -- Lifecycle --

    async def start(self) -> None:
        """Start watching for file changes."""
        if self._running:
            return

        self._running = True

        if not self.watch_path.exists():
            logger.warning("Watch path does not exist: %s", self.watch_path)
            return

        if self._use_polling:
            await self._start_polling()
        else:
            self._start_watchdog()

        logger.info("File watch started for %s (mode=%s)", self.watch_path, "polling" if self._use_polling else "watchdog")

    async def stop(self) -> None:
        """Stop watching for file changes."""
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        if self._debounce_task:
            self._debounce_task.cancel()
            self._debounce_task = None

        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None

        logger.info("File watch stopped for %s", self.watch_path)

    # -- Watchdog Mode --

    def _start_watchdog(self) -> None:
        """Start watchdog observer."""
        handler = _WatchdogHandler(self._on_file_event)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.watch_path), recursive=True)
        self._observer.start()

    def _on_file_event(self, file_path: str) -> None:
        """Handle a file change event."""
        # Filter by extension
        if self._scan_extensions:
            ext = Path(file_path).suffix.lower()
            if ext not in self._scan_extensions:
                return

        self._pending_changes.add(file_path)
        self._schedule_debounce()

    def _schedule_debounce(self) -> None:
        """Schedule a debounced flush of pending changes."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()

        async def _debounced_flush():
            await asyncio.sleep(self._debounce_seconds)
            if self._pending_changes:
                changes = list(self._pending_changes)
                self._pending_changes.clear()
                self._on_change(changes)

        self._debounce_task = asyncio.create_task(_debounced_flush())

    # -- Polling Mode --

    async def _start_polling(self) -> None:
        """Start polling-based change detection."""
        # Build initial mtime snapshot
        self._file_mtimes = self._scan_mtimes()

        async def _poll_loop():
            while self._running:
                try:
                    await asyncio.sleep(self._poll_interval)
                    if not self._running:
                        break
                    self._check_for_changes()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Polling error: %s", e)

        self._poll_task = asyncio.create_task(_poll_loop())

    def _scan_mtimes(self) -> dict[str, float]:
        """Scan all files and return their modification times."""
        mtimes: dict[str, float] = {}
        for dirpath, dirnames, filenames in os.walk(self.watch_path):
            # Filter directories
            dirnames[:] = [d for d in dirnames if d not in self._ignore_dirs]

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Filter by extension
                if self._scan_extensions:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in self._scan_extensions:
                        continue

                try:
                    mtimes[file_path] = os.path.getmtime(file_path)
                except OSError:
                    pass

        return mtimes

    def _check_for_changes(self) -> None:
        """Check for file changes since last poll."""
        changed_files: list[str] = []

        # Check existing files for changes
        for file_path, old_mtime in list(self._file_mtimes.items()):
            try:
                new_mtime = os.path.getmtime(file_path)
                if new_mtime > old_mtime:
                    changed_files.append(file_path)
                    self._file_mtimes[file_path] = new_mtime
            except OSError:
                # File was deleted
                changed_files.append(file_path)
                del self._file_mtimes[file_path]

        # Check for new files
        new_mtimes = self._scan_mtimes()
        for file_path, mtime in new_mtimes.items():
            if file_path not in self._file_mtimes:
                changed_files.append(file_path)
                self._file_mtimes[file_path] = mtime

        if changed_files:
            self._on_change(changed_files)


# ---------------------------------------------------------------------------
# Watchdog Handler
# ---------------------------------------------------------------------------


if _HAS_WATCHDOG:

    class _WatchdogHandler(FileSystemEventHandler):
        """Watchdog event handler that forwards to the manager."""

        def __init__(self, callback: Callable[[str], None]):
            super().__init__()
            self._callback = callback

        def on_modified(self, event):
            if not event.is_directory:
                self._callback(event.src_path)

        def on_created(self, event):
            if not event.is_directory:
                self._callback(event.src_path)