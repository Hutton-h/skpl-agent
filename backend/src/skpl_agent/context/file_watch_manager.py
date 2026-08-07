"""File watch manager — re-exports from app-level manager.

The core implementation lives in :mod:`skpl_agent.app._manager._file_watch_manager`.
This module exists to provide the expected ``context.file_watch_manager`` import path.
"""

from skpl_agent.app._manager._file_watch_manager import FileWatchManager

__all__ = ["FileWatchManager"]