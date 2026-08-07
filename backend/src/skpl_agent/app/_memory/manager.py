"""SKPL Memory Manager — Unified memory orchestration across L1-L4 layers.

Layers:
- **L1 (Working Memory)**: Cerebrum — agent's current session knowledge.
  Persisted via CerebrumRow in SQL, shared across devices via VPS.
- **L2 (Semantic Memory)**: Mem0 — long-term user memory with vector
  search. Stores user preferences, learned facts, and patterns.
- **L3 (Episodic Memory)**: KnowledgeBase — documents, indexed
  content, and session history with org-scoped visibility.
- **L4 (Procedural Memory)**: Vector store — embedding-based recall
  for agent workflows and patterns.

All memory is stored on VPS and accessible from any device (desktop
node, mobile PWA) via the same API.

Cross-device bridging:
  Sessions are linked to a ``device_id`` so the same user can switch
  devices mid-conversation. The MemoryManager provides device-aware
  recall so L1-L2 context follows the user.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unified memory orchestration for SKPL agents.

    Wraps the three memory subsystems (Cerebrum, Mem0, KnowledgeBase)
    and provides a single interface for agents to store and retrieve
    memories across all layers.

    Usage:
        >>> mem = MemoryManager(storage, cerebrum_service, kb_service)
        >>> await mem.remember("user_preference", "dark mode", layer="l2")
        >>> results = await mem.recall("user_preference", layers=["l1", "l2"])
    """

    def __init__(
        self,
        storage,
        cerebrum_service=None,
        mem0_client=None,
        kb_service=None,
    ):
        """Initialize the memory manager.

        Args:
            storage: AsyncSQLAlchemyStorage instance.
            cerebrum_service: CerebrumService for L1 working memory.
            mem0_client: Mem0 client for L2 semantic memory (optional).
            kb_service: KnowledgeBaseService for L3 episodic memory (optional).
        """
        self._storage = storage
        self._cerebrum = cerebrum_service
        self._mem0 = mem0_client
        self._kb = kb_service

    # ------------------------------------------------------------------
    # Context Assembly (cross-device)
    # ------------------------------------------------------------------

    async def assemble_context(
        self,
        user_id: str,
        session_id: str | None = None,
        device_id: str | None = None,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Assemble all relevant memory context for a user/session.

        Called at the start of each chat turn to inject memory into
        the agent's system prompt. Searches across all layers and
        returns a combined context dict.

        Args:
            user_id: User UUID.
            session_id: Current session ID (for L1 scoping).
            device_id: Current device ID (for cross-device bridging).
            max_tokens: Maximum token budget for context.

        Returns:
            dict with keys: ``l1_memories``, ``l2_memories``,
            ``l3_memories``, ``cross_device_hint``, ``total_tokens``.
        """
        context: dict[str, Any] = {
            "l1_memories": [],
            "l2_memories": [],
            "l3_memories": [],
            "cross_device_hint": None,
            "total_tokens": 0,
        }

        # L1: Working memory (Cerebrum)
        if self._cerebrum is not None:
            try:
                memories = self._cerebrum.get_all()
                context["l1_memories"] = [
                    {"key": m.key, "value": m.value, "category": m.category}
                    for m in memories[:50]
                ]
            except Exception as e:
                logger.warning("L1 memory recall failed: %s", e)

        # L2: Semantic memory (Mem0)
        if self._mem0 is not None and session_id is not None:
            try:
                # Mem0 search for relevant user memories
                context["l2_memories"] = await self._search_mem0(
                    user_id, session_id, limit=10
                )
            except Exception as e:
                logger.warning("L2 memory recall failed: %s", e)

        # L3: Episodic memory (KnowledgeBase)
        if self._kb is not None:
            try:
                context["l3_memories"] = await self._search_knowledge(
                    user_id, limit=5
                )
            except Exception as e:
                logger.warning("L3 memory recall failed: %s", e)

        # Cross-device bridging
        if device_id is not None:
            context["cross_device_hint"] = await self._get_device_context(
                user_id, device_id
            )

        return context

    # ------------------------------------------------------------------
    # Memory Storage
    # ------------------------------------------------------------------

    async def remember(
        self,
        key: str,
        value: str,
        layer: str = "l1",
        user_id: str = "",
        session_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store a memory in the specified layer.

        Args:
            key: Memory key/identifier.
            value: Memory content.
            layer: Target layer (l1, l2, l3).
            user_id: User UUID (required for l2/l3).
            session_id: Session ID (for scoping).
            metadata: Additional metadata.

        Returns:
            True if stored successfully.
        """
        try:
            if layer == "l1" and self._cerebrum is not None:
                self._cerebrum.remember(
                    key=key,
                    value=value,
                    category=metadata.get("category", "general") if metadata else "general",
                    confidence=metadata.get("confidence", 1.0) if metadata else 1.0,
                    source=metadata.get("source") if metadata else None,
                )
                return True

            elif layer == "l2" and self._mem0 is not None:
                await self._mem0.add(
                    messages=[{"role": "user", "content": value}],
                    user_id=user_id,
                    metadata={"key": key, **metadata} if metadata else {"key": key},
                )
                return True

            elif layer == "l3" and self._kb is not None:
                # L3 is handled via KnowledgeBase file uploads;
                # text-based memories are stored in L2 instead.
                logger.debug("L3 memory storage delegated to KnowledgeBase upload API")
                return False

        except Exception as e:
            logger.error("Memory storage failed (layer=%s, key=%s): %s", layer, key, e)
            return False

        return False

    async def recall(
        self,
        key: str,
        layers: list[str] | None = None,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Recall a memory across specified layers.

        Args:
            key: Memory key to search for.
            layers: Layers to search (default: all).
            user_id: User UUID.

        Returns:
            dict with layer -> result mapping.
        """
        if layers is None:
            layers = ["l1", "l2", "l3"]

        results: dict[str, Any] = {}

        if "l1" in layers and self._cerebrum is not None:
            mem = self._cerebrum.recall(key)
            if mem:
                results["l1"] = {"key": mem.key, "value": mem.value, "category": mem.category}

        if "l2" in layers and self._mem0 is not None:
            try:
                mem0_results = await self._mem0.search(key, user_id=user_id, limit=3)
                if mem0_results:
                    results["l2"] = [{"content": r.get("memory", ""), "score": r.get("score", 0)} for r in mem0_results]
            except Exception as e:
                logger.warning("L2 recall failed: %s", e)

        if "l3" in layers and self._kb is not None:
            try:
                kb_results = await self._search_knowledge(user_id, query=key, limit=3)
                if kb_results:
                    results["l3"] = kb_results
            except Exception as e:
                logger.warning("L3 recall failed: %s", e)

        return results

    # ------------------------------------------------------------------
    # Cross-device session bridging
    # ------------------------------------------------------------------

    async def bridge_session(
        self,
        user_id: str,
        session_id: str,
        device_id: str,
    ) -> dict[str, Any]:
        """Bridge a session to a new device so the user can continue from
        another device.

        Associates the session with the device_id and returns the
        assembled context so the agent can pick up where it left off.

        Args:
            user_id: User UUID.
            session_id: Session to bridge.
            device_id: Target device identifier.

        Returns:
            dict with ``session_id``, ``device_id``, ``context``,
            ``last_message_at``.
        """
        # Update session device_id
        try:
            from skpl_agent.app.storage._sql._tables import SessionRow

            async with self._storage._session() as sess:
                session = await sess.get(SessionRow, session_id)
                if session is not None:
                    session.device_id = device_id
                    await sess.commit()
                    logger.info(
                        "Session %s bridged to device %s for user %s",
                        session_id, device_id, user_id,
                    )
        except Exception as e:
            logger.warning("Failed to update session device_id: %s", e)

        # Assemble context for the new device
        context = await self.assemble_context(
            user_id=user_id,
            session_id=session_id,
            device_id=device_id,
        )

        return {
            "session_id": session_id,
            "device_id": device_id,
            "context": context,
            "bridged_at": datetime.now(timezone.utc).isoformat(),
        }

    async def list_device_sessions(
        self,
        user_id: str,
        device_id: str,
    ) -> list[dict[str, Any]]:
        """List all sessions associated with a specific device.

        Args:
            user_id: User UUID.
            device_id: Device identifier.

        Returns:
            List of session summaries.
        """
        try:
            from skpl_agent.app.storage._sql._tables import SessionRow

            async with self._storage._session() as sess:
                result = await sess.execute(
                    select(SessionRow).where(
                        SessionRow.user_id == user_id,
                        SessionRow.device_id == device_id,
                    )
                )
                sessions = result.scalars().all()
                if not sessions:
                    return []

                return [
                    {
                        "session_id": s.id,
                        "agent_id": s.agent_id,
                        "source": s.source,
                        "device_id": s.device_id,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                    }
                    for s in sessions
                ]
        except Exception as e:
            logger.warning("Failed to list device sessions: %s", e)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _search_mem0(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search Mem0 for relevant memories."""
        if self._mem0 is None:
            return []
        try:
            results = await self._mem0.search(query, user_id=user_id, limit=limit)
            return [
                {
                    "memory": r.get("memory", ""),
                    "score": r.get("score", 0),
                    "metadata": r.get("metadata", {}),
                }
                for r in (results or [])
            ]
        except Exception:
            return []

    async def _search_knowledge(
        self,
        user_id: str,
        query: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search knowledge bases for relevant content."""
        if self._kb is None:
            return []
        try:
            # List user's accessible knowledge bases
            kbs = await self._kb.list_knowledge_bases(user_id)
            return [
                {"kb_id": kb.get("id", ""), "name": kb.get("name", ""), "description": kb.get("description", "")}
                for kb in (kbs or [])[:limit]
            ]
        except Exception:
            return []

    async def _get_device_context(
        self,
        user_id: str,
        device_id: str,
    ) -> dict[str, Any] | None:
        """Get context about the user's other active devices."""
        try:
            from skpl_agent.app.storage._sql._tables import SessionRow

            async with self._storage._session() as sess:
                result = await sess.execute(
                    select(SessionRow).where(SessionRow.user_id == user_id)
                )
                sessions = result.scalars().all()
                if not sessions:
                    return None

                # Count sessions per device
                device_counts: dict[str, int] = {}
                for s in sessions:
                    if s.device_id:
                        device_counts[s.device_id] = device_counts.get(s.device_id, 0) + 1

                other_devices = {k: v for k, v in device_counts.items() if k != device_id}

                return {
                    "current_device": device_id,
                    "other_active_devices": len(other_devices),
                    "device_summary": other_devices,
                }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def connect_kb_service(self, kb_service) -> None:
        """Connect a KnowledgeBaseService after initialization.

        Called from lifespan() once the KB service is ready, since
        MemoryManager is created in _setup_auth() before lifespan.
        """
        self._kb = kb_service
        logger.info("MemoryManager: KnowledgeBase service connected (L3)")

    def connect_mem0(self, mem0_client) -> None:
        """Connect a Mem0 client after initialization."""
        self._mem0 = mem0_client
        logger.info("MemoryManager: Mem0 client connected (L2)")

    def health(self) -> dict[str, bool]:
        """Check the health of all memory subsystems."""
        return {
            "l1_cerebrum": self._cerebrum is not None,
            "l2_mem0": self._mem0 is not None,
            "l3_knowledge": self._kb is not None,
        }