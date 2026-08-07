"""Cerebrum Service — Business logic for agent memory management.

Provides CRUD operations, TTL-based expiration, confidence scoring,
and access tracking for the agent's learned knowledge.
"""

from __future__ import annotations

import logging
from typing import Optional

from skpl_agent.context.cerebrum import Cerebrum, Memory

logger = logging.getLogger(__name__)


class CerebrumService:
    """Service for agent memory (cerebrum) management.

    Wraps Cerebrum to provide:
    - Memory CRUD with TTL support
    - Confidence-based retrieval
    - Access tracking and analytics
    - Category-based organization
    """

    def __init__(self, agent_id: str = "", max_entries: int = 10000):
        self._cerebrum = Cerebrum(agent_id=agent_id, max_entries=max_entries)

    # ── CRUD Operations ────────────────────────────────────────────────────

    def remember(
        self,
        key: str,
        value: str,
        category: str = "general",
        confidence: float = 1.0,
        source: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Memory:
        """Store a new memory or update an existing one."""
        return self._cerebrum.remember(
            key=key,
            value=value,
            category=category,
            confidence=confidence,
            source=source,
            ttl_seconds=ttl_seconds,
        )

    def recall(self, key: str, default: str | None = None) -> Memory | None:
        """Retrieve a memory by key. Updates access count."""
        return self._cerebrum.recall(key, default)

    def forget(self, key: str) -> bool:
        """Remove a memory by key."""
        return self._cerebrum.forget(key)

    def update(
        self,
        key: str,
        value: str | None = None,
        confidence: float | None = None,
        category: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Memory | None:
        """Update a memory's fields."""
        return self._cerebrum.update(
            key=key,
            value=value,
            confidence=confidence,
            category=category,
            ttl_seconds=ttl_seconds,
        )

    # ── Query Operations ───────────────────────────────────────────────────

    def get_by_category(self, category: str) -> list[Memory]:
        """Get all memories in a category."""
        return self._cerebrum.get_by_category(category)

    def get_all(self) -> list[Memory]:
        """Get all non-expired memories."""
        return self._cerebrum.get_all()

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Memory]:
        """Search memories by key or value content."""
        return self._cerebrum.search(query=query, limit=limit)

    def get_high_confidence(
        self,
        threshold: float = 0.8,
    ) -> list[Memory]:
        """Get memories with confidence above the threshold."""
        return self._cerebrum.get_high_confidence(threshold=threshold)

    def get_frequently_accessed(
        self,
        min_access: int = 5,
    ) -> list[Memory]:
        """Get memories that have been accessed frequently."""
        return self._cerebrum.get_frequently_accessed(min_access=min_access)

    # ── Bulk Operations ────────────────────────────────────────────────────

    def export_context(self, max_entries: int = 50) -> str:
        """Export memories as a context string for injection into prompts."""
        return self._cerebrum.export_context(max_entries=max_entries)

    def import_from_dict(self, data: dict[str, dict]) -> int:
        """Import memories from a dict. Returns count of imported memories."""
        return self._cerebrum.import_from_dict(data)

    def to_dict(self) -> dict[str, dict]:
        """Export all memories as a dict."""
        return self._cerebrum.to_dict()

    # ── Statistics ─────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get memory statistics."""
        return self._cerebrum.get_stats()

    # ── Maintenance ────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all memories."""
        self._cerebrum.clear()

    @property
    def total_count(self) -> int:
        stats = self._cerebrum.get_stats()
        return stats.get("total_memories", 0)