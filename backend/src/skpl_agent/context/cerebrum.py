"""
Cerebrum — Agent learning memory and knowledge persistence.

Provides a key-value store for agent "brain" state, enabling agents
to remember facts, preferences, patterns, and learned behaviors across
sessions. Supports TTL-based expiration, confidence scoring, and
access tracking.

Based on OpenWolf's Cerebrum learning memory system.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class Memory:
    """A single memory entry in the cerebrum."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    key: str = ""
    value: str = ""
    category: str = "general"
    confidence: float = 1.0
    source: str | None = None
    ttl_seconds: int | None = None
    access_count: int = 0
    last_accessed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if the memory has expired."""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds


# ---------------------------------------------------------------------------
# Cerebrum Manager
# ---------------------------------------------------------------------------


class Cerebrum:
    """Agent learning memory manager.

    Usage:
        brain = Cerebrum(agent_id="agent-123")
        brain.remember("user_preference", "dark_mode", category="preferences")
        pref = brain.recall("user_preference")
        if pref:
            print(f"User prefers: {pref.value}")
    """

    def __init__(self, agent_id: str = "", max_entries: int = 10000):
        self.agent_id = agent_id
        self.max_entries = max_entries
        self._memories: dict[str, Memory] = {}
        self._key_index: dict[str, str] = {}  # key → memory_id

    # -- CRUD --

    def remember(
        self,
        key: str,
        value: str,
        category: str = "general",
        confidence: float = 1.0,
        source: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Memory:
        """Store a memory. Overwrites existing memory with the same key."""
        # Check if key already exists
        existing_id = self._key_index.get(key)
        if existing_id and existing_id in self._memories:
            mem = self._memories[existing_id]
            mem.value = value
            mem.category = category
            mem.confidence = confidence
            mem.source = source
            mem.ttl_seconds = ttl_seconds
            mem.updated_at = datetime.now(timezone.utc)
            return mem

        memory = Memory(
            agent_id=self.agent_id,
            key=key,
            value=value,
            category=category,
            confidence=confidence,
            source=source,
            ttl_seconds=ttl_seconds,
        )
        self._memories[memory.id] = memory
        self._key_index[key] = memory.id

        # Trim if over max
        self._trim()

        return memory

    def recall(self, key: str, default: str | None = None) -> Memory | None:
        """Retrieve a memory by key. Returns None if not found or expired."""
        memory_id = self._key_index.get(key)
        if memory_id is None:
            return None

        memory = self._memories.get(memory_id)
        if memory is None:
            self._key_index.pop(key, None)
            return None

        if memory.is_expired:
            self.forget(key)
            return None

        memory.access_count += 1
        memory.last_accessed_at = datetime.now(timezone.utc)
        return memory

    def forget(self, key: str) -> bool:
        """Remove a memory by key."""
        memory_id = self._key_index.pop(key, None)
        if memory_id and memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def update(
        self,
        key: str,
        value: str | None = None,
        confidence: float | None = None,
        category: str | None = None,
        ttl_seconds: int | None = None,
    ) -> Memory | None:
        """Update a memory's fields."""
        memory = self.recall(key)
        if memory is None:
            return None

        if value is not None:
            memory.value = value
        if confidence is not None:
            memory.confidence = confidence
        if category is not None:
            memory.category = category
        if ttl_seconds is not None:
            memory.ttl_seconds = ttl_seconds

        memory.updated_at = datetime.now(timezone.utc)
        return memory

    # -- Queries --

    def get_by_category(self, category: str) -> list[Memory]:
        """Get all memories in a category."""
        self._cleanup_expired()
        return [m for m in self._memories.values() if m.category == category]

    def get_all(self) -> list[Memory]:
        """Get all non-expired memories."""
        self._cleanup_expired()
        return list(self._memories.values())

    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """Search memories by key or value substring."""
        self._cleanup_expired()
        query_lower = query.lower()
        results = [
            m
            for m in self._memories.values()
            if query_lower in m.key.lower() or query_lower in m.value.lower()
        ]
        results.sort(key=lambda m: m.access_count, reverse=True)
        return results[:limit]

    def get_high_confidence(self, threshold: float = 0.8) -> list[Memory]:
        """Get memories with high confidence."""
        self._cleanup_expired()
        return [m for m in self._memories.values() if m.confidence >= threshold]

    def get_frequently_accessed(self, min_access: int = 5) -> list[Memory]:
        """Get memories accessed frequently."""
        self._cleanup_expired()
        return [m for m in self._memories.values() if m.access_count >= min_access]

    # -- Bulk Operations --

    def export_context(self, max_entries: int = 50) -> str:
        """Export memories as a context string for injection into prompts."""
        self._cleanup_expired()
        entries = sorted(
            self._memories.values(),
            key=lambda m: (m.confidence * m.access_count),
            reverse=True,
        )[:max_entries]

        if not entries:
            return ""

        lines = ["## Agent Memory (Cerebrum)"]
        for mem in entries:
            line = f"- [{mem.category}] {mem.key}: {mem.value}"
            if mem.confidence < 1.0:
                line += f" (confidence: {mem.confidence:.0%})"
            lines.append(line)

        return "\n".join(lines)

    def import_from_dict(self, data: dict[str, dict]) -> int:
        """Import memories from a dict. Returns count of imported memories."""
        count = 0
        for key, info in data.items():
            self.remember(
                key=key,
                value=info.get("value", ""),
                category=info.get("category", "general"),
                confidence=info.get("confidence", 1.0),
                source=info.get("source"),
                ttl_seconds=info.get("ttl_seconds"),
            )
            count += 1
        return count

    def to_dict(self) -> dict[str, dict]:
        """Export all memories as a dict."""
        self._cleanup_expired()
        return {
            m.key: {
                "value": m.value,
                "category": m.category,
                "confidence": m.confidence,
                "source": m.source,
                "ttl_seconds": m.ttl_seconds,
                "access_count": m.access_count,
            }
            for m in self._memories.values()
        }

    # -- Stats --

    def get_stats(self) -> dict:
        """Get cerebrum statistics."""
        self._cleanup_expired()
        by_category: dict[str, int] = {}
        total_confidence = 0.0

        for m in self._memories.values():
            by_category[m.category] = by_category.get(m.category, 0) + 1
            total_confidence += m.confidence

        return {
            "total_memories": len(self._memories),
            "by_category": by_category,
            "avg_confidence": (
                total_confidence / len(self._memories) if self._memories else 0.0
            ),
            "total_accesses": sum(m.access_count for m in self._memories.values()),
        }

    def clear(self) -> None:
        """Clear all memories."""
        self._memories.clear()
        self._key_index.clear()

    # -- Internal --

    def _cleanup_expired(self) -> None:
        """Remove expired memories."""
        expired_keys = []
        for key, mem_id in self._key_index.items():
            mem = self._memories.get(mem_id)
            if mem and mem.is_expired:
                expired_keys.append(key)

        for key in expired_keys:
            self.forget(key)

    def _trim(self) -> None:
        """Trim to max entries, removing least valuable memories first."""
        if len(self._memories) <= self.max_entries:
            return

        # Sort by value (confidence * access_count), remove lowest
        sorted_mems = sorted(
            self._memories.values(),
            key=lambda m: m.confidence * m.access_count,
        )
        to_remove = len(self._memories) - self.max_entries

        for mem in sorted_mems[:to_remove]:
            self._key_index.pop(mem.key, None)
            del self._memories[mem.id]