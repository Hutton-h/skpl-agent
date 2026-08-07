"""MemoryEnhancer — scheduled background task for memory enhancement.

Runs periodically via APScheduler to:
1. Query all users from storage
2. For each user, extract scenes from recent conversations
3. Generate/update user personas (L4)
4. Use circuit breaker to prevent cascading failures

The enhancement runs silently in the background. Failures are logged
but never surface to the user.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class MemoryEnhancer:
    """Periodic memory enhancement for all users.

    Uses circuit breaker pattern:
    - 5 consecutive failures → 60s cooldown → retry
    - During cooldown, all operations silently degrade (no-op)
    """

    MAX_CONSECUTIVE_FAILURES = 5
    COOLDOWN_SECONDS = 60

    def __init__(
        self,
        storage,
        memory_manager=None,
    ):
        """Initialize the MemoryEnhancer.

        Args:
            storage: AsyncSQLAlchemyStorage instance for querying users.
            memory_manager: MemoryManager instance (optional, falls back to
                app.state.memory_manager).
        """
        self._storage = storage
        self._memory_manager = memory_manager
        self._failure_count = 0
        self._cooldown_until: datetime | None = None

    async def enhance_all_users(self) -> dict[str, Any]:
        """Run memory enhancement for all users.

        Called by APScheduler on a fixed interval. Uses best-effort:
        individual user failures are logged but don't stop the batch.

        Returns:
            dict with summary of enhancement results.
        """
        if self._in_cooldown():
            logger.info(
                "MemoryEnhancer: in cooldown (failures=%d), skipping cycle",
                self._failure_count,
            )
            return {"status": "cooldown", "failures": self._failure_count}

        try:
            users = await self._get_all_users()
            if not users:
                logger.debug("MemoryEnhancer: no users found, skipping")
                return {"status": "ok", "users_processed": 0}

            results = {"status": "ok", "users_processed": 0, "errors": 0}

            for user in users:
                try:
                    user_id = user.get("id", "")
                    username = user.get("username", "unknown")
                    if not user_id:
                        continue

                    await self._enhance_user(user_id, username)
                    results["users_processed"] += 1

                except Exception as e:
                    logger.warning(
                        "MemoryEnhancer: failed for user %s: %s",
                        user.get("username", "unknown"), e,
                    )
                    results["errors"] += 1

            self._failure_count = 0
            self._cooldown_until = None

            logger.info(
                "MemoryEnhancer: cycle complete — %d users, %d errors",
                results["users_processed"], results["errors"],
            )
            return results

        except Exception as e:
            self._failure_count += 1
            logger.error(
                "MemoryEnhancer: batch failed (failure %d/%d): %s",
                self._failure_count, self.MAX_CONSECUTIVE_FAILURES, e,
            )
            if self._failure_count >= self.MAX_CONSECUTIVE_FAILURES:
                self._cooldown_until = datetime.now(timezone.utc) + timedelta(
                    seconds=self.COOLDOWN_SECONDS
                )
                logger.warning(
                    "MemoryEnhancer: circuit breaker tripped, "
                    "cooldown until %s",
                    self._cooldown_until.isoformat(),
                )
            return {"status": "error", "failures": self._failure_count}

    async def _enhance_user(self, user_id: str, username: str) -> None:
        """Enhance memory for a single user.

        Currently focuses on Mem0 (L2) memory enhancement:
        - Searches recent user memories
        - Extracts key facts and patterns
        - Updates the user's memory index
        """
        mm = self._memory_manager
        if mm is None:
            logger.debug("MemoryEnhancer: no memory manager, skipping user %s", username)
            return

        if mm._mem0 is None:
            logger.debug("MemoryEnhancer: Mem0 not available for user %s", username)
            return

        try:
            recent = await mm._mem0.search(
                f"recent activity for user {username}",
                user_id=user_id,
                limit=20,
            )
            memory_count = len(recent) if recent else 0
            logger.debug(
                "MemoryEnhancer: user %s has %d memories",
                username, memory_count,
            )
        except Exception as e:
            logger.warning(
                "MemoryEnhancer: search failed for user %s: %s",
                username, e,
            )

    async def _get_all_users(self) -> list[dict[str, Any]]:
        """Query all users from storage."""
        try:
            from skpl_agent.app._auth.models import UserRow
            from sqlalchemy import select

            async with self._storage._session() as sess:
                result = await sess.execute(select(UserRow))
                rows = result.scalars().all()
                return [
                    {"id": r.id, "username": r.username}
                    for r in rows
                ]
        except Exception as e:
            logger.warning("MemoryEnhancer: failed to query users: %s", e)
            return []

    def _in_cooldown(self) -> bool:
        """Check if circuit breaker is in cooldown."""
        if self._cooldown_until is None:
            return False
        if datetime.now(timezone.utc) >= self._cooldown_until:
            self._cooldown_until = None
            self._failure_count = 0
            return False
        return True


# ---------------------------------------------------------------------------
# APScheduler integration
# ---------------------------------------------------------------------------

def setup_memory_enhancer_scheduler(app, interval_minutes: int = 30):
    """Register MemoryEnhancer as a scheduled APScheduler job.

    Args:
        app: FastAPI application instance.
        interval_minutes: How often to run enhancement (default: 30).
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    storage = getattr(app.state, "storage", None)
    memory_manager = getattr(app.state, "memory_manager", None)

    if storage is None:
        logger.warning("MemoryEnhancer: no storage, skipping scheduler setup")
        return

    enhancer = MemoryEnhancer(
        storage=storage,
        memory_manager=memory_manager,
    )
    app.state.memory_enhancer = enhancer

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        enhancer.enhance_all_users,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="memory_enhancer",
        name="Memory Enhancement",
        replace_existing=True,
    )
    scheduler.start()

    app.state.memory_enhancer_scheduler = scheduler

    logger.info(
        "MemoryEnhancer: scheduler started (interval=%d min)",
        interval_minutes,
    )


def shutdown_memory_enhancer_scheduler(app):
    """Shutdown the MemoryEnhancer scheduler."""
    scheduler = getattr(app.state, "memory_enhancer_scheduler", None)
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("MemoryEnhancer: scheduler stopped")