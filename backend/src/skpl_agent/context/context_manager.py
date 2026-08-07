"""Context manager — re-exports from app-level manager.

The core implementation lives in :mod:`skpl_agent.app._manager._context_manager`.
This module exists to provide the expected ``context.context_manager`` import path.
"""

from skpl_agent.app._manager._context_manager import ContextManager

__all__ = ["ContextManager"]