"""
Cross-Process Anatomy Lock — Prevents concurrent write conflicts.

Uses file-based locking (flock on Unix, msvcrt on Windows) to ensure
only one process or thread writes to the anatomy store at a time.
Designed for the scenario where file watchers may trigger scans
concurrently with manual scans.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


class AnatomyLock:
    """Cross-process file lock for anatomy store operations.

    Usage:
        lock = AnatomyLock("/path/to/.skpl/anatomy.lock")
        with lock.acquire(timeout=5.0):
            # Safe to write to the anatomy store
            store.upsert_symbol(...)
    """

    def __init__(self, lock_path: str | Path):
        self.lock_path = Path(lock_path)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_fd: Optional[int] = None

    @contextmanager
    def acquire(self, timeout: float = 10.0):
        """Acquire the lock, waiting up to `timeout` seconds.

        Yields control to the caller. Automatically releases on exit.
        """
        fd = self._acquire_lock(timeout)
        try:
            yield
        finally:
            self._release_lock(fd)

    def _acquire_lock(self, timeout: float) -> int:
        """Acquire a file lock. Returns the file descriptor."""
        fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR)

        if os.name == "nt":
            # Windows: use msvcrt locking
            import msvcrt

            start = time.monotonic()
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() - start > timeout:
                        os.close(fd)
                        raise TimeoutError(
                            f"Could not acquire anatomy lock within {timeout}s"
                        )
                    time.sleep(0.05)
        else:
            # Unix: use fcntl.flock
            import fcntl

            start = time.monotonic()
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() - start > timeout:
                        os.close(fd)
                        raise TimeoutError(
                            f"Could not acquire anatomy lock within {timeout}s"
                        )
                    time.sleep(0.05)

        self._lock_fd = fd
        return fd

    def _release_lock(self, fd: int) -> None:
        """Release the file lock and close the file descriptor."""
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            self._lock_fd = None

    def is_locked(self) -> bool:
        """Check if the lock is currently held by any process."""
        if not self.lock_path.exists():
            return False
        try:
            fd = os.open(str(self.lock_path), os.O_RDONLY)
            if os.name == "nt":
                import msvcrt

                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    return False
                except OSError:
                    return True
            else:
                import fcntl

                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    return False
                except BlockingIOError:
                    return True
        finally:
            try:
                os.close(fd)
            except OSError:
                pass


class NoOpLock:
    """A lock that does nothing — for single-process or testing use."""

    @contextmanager
    def acquire(self, timeout: float = 10.0):
        yield

    def is_locked(self) -> bool:
        return False