"""Scan task manager — re-exports from app-level manager.

The core implementation lives in :mod:`skpl_agent.app._manager.scan_task_manager`.
This module exists to provide the expected ``context.scan_task_manager`` import path.
"""

from skpl_agent.app._manager._scan_task_manager import ScanTaskManager

__all__ = ["ScanTaskManager"]