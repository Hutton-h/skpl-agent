"""Context injector — manage contextual information for agent sessions.

Provides session-aware context injection, retrieval, and clearing
for the SKPL Agent context management subsystem.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context that can be injected into a session."""

    PROJECT = "project"
    FILE = "file"
    SYMBOL = "symbol"
    BUG = "bug"
    MEMORY = "memory"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class ContextEntry:
    """A single context entry within a session.

    Attributes:
        entry_id: Unique identifier for this entry.
        context_type: The type of context.
        content: The actual context data.
        metadata: Optional metadata about the context.
        created_at: Unix timestamp of creation.
        expires_at: Optional expiration timestamp.
        priority: Priority level (higher = more important).
        tags: Optional categorization tags.
    """

    entry_id: str
    context_type: ContextType
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    priority: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        """Check if this context entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class ContextInjector:
    """Manages contextual information injection for agent sessions.

    Supports injecting, retrieving, and clearing context entries
    organized by session ID and context type.

    Usage:
        >>> injector = ContextInjector()
        >>> injector.inject_context(
        ...     session_id="session-001",
        ...     context_type=ContextType.PROJECT,
        ...     content={"name": "my-project", "path": "/src"},
        ... )
        >>> contexts = injector.get_active_contexts("session-001")
        >>> injector.clear_context("session-001", ContextType.PROJECT)
    """

    def __init__(self) -> None:
        # session_id -> list[ContextEntry]
        self._sessions: dict[str, list[ContextEntry]] = {}

    # ── Main API ─────────────────────────────────────────────────────────

    def inject_context(
        self,
        session_id: str,
        context_type: ContextType | str,
        content: Any,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: float | None = None,
        priority: int = 0,
        tags: list[str] | None = None,
    ) -> ContextEntry:
        """Inject a context entry into a session.

        Args:
            session_id: Identifier for the target session.
            context_type: The type of context to inject.
            content: The context data to inject.
            metadata: Optional metadata about the context.
            ttl_seconds: Optional time-to-live in seconds.
            priority: Priority level (higher = more important).
            tags: Optional categorization tags.

        Returns:
            The created ContextEntry.
        """
        import uuid

        if isinstance(context_type, str):
            context_type = ContextType(context_type)

        entry_id = str(uuid.uuid4())[:8]
        now = time.time()

        entry = ContextEntry(
            entry_id=entry_id,
            context_type=context_type,
            content=content,
            metadata=metadata or {},
            created_at=now,
            expires_at=now + ttl_seconds if ttl_seconds is not None else None,
            priority=priority,
            tags=tags or [],
        )

        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append(entry)

        logger.info(
            "Injected context [%s] type=%s into session=%s (priority=%d)",
            entry_id, context_type.value, session_id, priority,
        )
        return entry

    def get_active_contexts(
        self,
        session_id: str,
        context_type: ContextType | str | None = None,
        include_expired: bool = False,
    ) -> list[ContextEntry]:
        """Get active (non-expired) context entries for a session.

        Args:
            session_id: Identifier for the target session.
            context_type: Optional filter by context type.
            include_expired: Whether to include expired entries.

        Returns:
            List of matching ContextEntry objects, sorted by priority
            (descending) then creation time (newest first).
        """
        if session_id not in self._sessions:
            logger.debug("No contexts found for session=%s", session_id)
            return []

        entries = self._sessions[session_id]

        # Filter by type
        if context_type is not None:
            if isinstance(context_type, str):
                context_type = ContextType(context_type)
            entries = [e for e in entries if e.context_type == context_type]

        # Filter expired
        if not include_expired:
            entries = [e for e in entries if not e.is_expired]

        # Sort: priority desc, then created_at desc
        entries.sort(key=lambda e: (-e.priority, -e.created_at))

        logger.debug(
            "Retrieved %d active contexts for session=%s (type=%s)",
            len(entries), session_id, context_type,
        )
        return entries

    def clear_context(
        self,
        session_id: str,
        context_type: ContextType | str | None = None,
    ) -> int:
        """Clear context entries from a session.

        Args:
            session_id: Identifier for the target session.
            context_type: Optional filter by context type. If None,
                          clears all context types for the session.

        Returns:
            Number of entries cleared.
        """
        if session_id not in self._sessions:
            return 0

        if context_type is None:
            count = len(self._sessions[session_id])
            del self._sessions[session_id]
            logger.info(
                "Cleared all %d context entries for session=%s", count, session_id,
            )
            return count

        if isinstance(context_type, str):
            context_type = ContextType(context_type)

        original_count = len(self._sessions[session_id])
        self._sessions[session_id] = [
            e for e in self._sessions[session_id]
            if e.context_type != context_type
        ]
        cleared = original_count - len(self._sessions[session_id])

        if not self._sessions[session_id]:
            del self._sessions[session_id]

        logger.info(
            "Cleared %d context entries (type=%s) for session=%s",
            cleared, context_type.value, session_id,
        )
        return cleared

    def expire_contexts(self, session_id: str) -> int:
        """Remove all expired context entries from a session.

        Args:
            session_id: Identifier for the target session.

        Returns:
            Number of expired entries removed.
        """
        if session_id not in self._sessions:
            return 0

        original_count = len(self._sessions[session_id])
        self._sessions[session_id] = [
            e for e in self._sessions[session_id] if not e.is_expired
        ]
        removed = original_count - len(self._sessions[session_id])

        if removed > 0:
            logger.debug(
                "Expired %d context entries for session=%s", removed, session_id,
            )

        return removed

    def list_sessions(self) -> list[str]:
        """List all active session IDs.

        Returns:
            List of session IDs that have context entries.
        """
        return list(self._sessions.keys())

    def get_context_summary(self, session_id: str) -> dict[str, int]:
        """Get a summary of context counts by type for a session.

        Args:
            session_id: Identifier for the target session.

        Returns:
            Dictionary mapping context type value to count.
        """
        if session_id not in self._sessions:
            return {}

        summary: dict[str, int] = {}
        for entry in self._sessions[session_id]:
            if not entry.is_expired:
                key = entry.context_type.value
                summary[key] = summary.get(key, 0) + 1
        return summary

    def clear_all(self) -> None:
        """Clear all context entries across all sessions."""
        count = sum(len(v) for v in self._sessions.values())
        self._sessions.clear()
        logger.info("Cleared all %d context entries across all sessions", count)