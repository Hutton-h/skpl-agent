"""ORM models for desktop-related tables.

Re-exports from the central _tables.py for modular access.
"""

from skpl_agent.app.storage._sql._tables import (
    DesktopActionLogRow,
    DesktopNodeRow,
    DesktopSessionRow,
)

__all__ = [
    "DesktopActionLogRow",
    "DesktopNodeRow",
    "DesktopSessionRow",
]