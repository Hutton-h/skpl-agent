"""Update Manager — APScheduler-based periodic update checking.

Manages the lifecycle of a scheduled job that periodically invokes
the upstream update checker. Uses APScheduler for reliable, production-grade
scheduling with configurable intervals.

Usage:
    >>> from skpl_agent.app._manager._update_manager import UpdateManager
    >>> from skpl_agent.updates import create_default_checker
    >>> checker = create_default_checker()
    >>> mgr = UpdateManager(checker=checker, check_interval_hours=6)
    >>> mgr.start()
    >>> # ... application runs ...
    >>> mgr.stop()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from skpl_agent.updates import UpdateChecker, UpdateReport, create_default_checker

logger = logging.getLogger(__name__)


class UpdateManager:
    """APScheduler-based manager for periodic upstream update checking.

    Wraps an UpdateChecker instance and schedules it to run at a configurable
    interval using APScheduler.  Provides start/stop lifecycle methods and
    status introspection.

    The scheduler runs in the same event loop as the FastAPI application
    and is torn down safely during application shutdown.

    Attributes:
        _checker: The underlying UpdateChecker instance.
        _scheduler: The APScheduler AsyncIOScheduler.
        _check_interval_hours: Hours between scheduled checks.
        _last_report: The most recent UpdateReport from a scheduled check.
        _last_run_time: The datetime of the most recent scheduled check.
    """

    # ── Job ID for the scheduled check ────────────────────────────────────
    _JOB_ID: str = "skpl_update_check"

    def __init__(
        self,
        checker: Optional[UpdateChecker] = None,
        check_interval_hours: int = 6,
    ) -> None:
        """Initialize the UpdateManager.

        Args:
            checker: An UpdateChecker instance. If None, defaults to
                     ``create_default_checker()`` with the four upstream repos.
            check_interval_hours: Interval in hours between scheduled checks.
        """
        self._checker = checker or create_default_checker()
        self._check_interval_hours = check_interval_hours

        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone="utc",
        )

        self._last_report: Optional[UpdateReport] = None
        self._last_run_time: Optional[datetime] = None
        self._running: bool = False

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the scheduled update checking.

        Registers an interval job with APScheduler and starts the scheduler.
        Idempotent — calling ``start()`` on an already-running manager is a
        no-op.
        """
        if self._running:
            logger.debug("UpdateManager is already running; skipping start()")
            return

        self._scheduler.add_job(
            func=self._scheduled_check,
            trigger=IntervalTrigger(hours=self._check_interval_hours),
            id=self._JOB_ID,
            name="SKPL upstream update check",
            replace_existing=True,
            misfire_grace_time=300,  # 5 min grace period for missed checks
        )

        self._scheduler.start()
        self._running = True
        logger.info(
            "UpdateManager started: interval=%dh, repos=%d",
            self._check_interval_hours,
            sum(1 for r in self._checker.get_repos() if r.enabled),
        )

    def stop(self) -> None:
        """Stop the scheduled update checking.

        Shuts down the APScheduler and waits for any in-flight check to
        complete.  Idempotent — calling ``stop()`` on an already-stopped
        manager is a no-op.
        """
        if not self._running:
            logger.debug("UpdateManager is not running; skipping stop()")
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        logger.info("UpdateManager stopped")

    # ── Scheduled Job ────────────────────────────────────────────────────────

    async def _scheduled_check(self) -> None:
        """Run a single update check (called by the scheduler).

        This method is the target of the APScheduler interval job. It invokes
        ``check_all()`` on the underlying checker, stores the result, and
        logs any errors that occur during the check.
        """
        start_time = datetime.now(timezone.utc)
        logger.debug("Scheduled update check started at %s", start_time.isoformat())

        try:
            report = await self._checker.check_all()
            self._last_report = report
            self._last_run_time = start_time

            if report.has_any_updates:
                updated = [r.repo_name for r in report.results if r.has_updates]
                logger.info(
                    "Scheduled check: %d/%d repos have updates: %s",
                    report.repos_with_updates,
                    report.total_repos,
                    ", ".join(updated),
                )
            else:
                logger.debug(
                    "Scheduled check: all %d repos are up-to-date",
                    report.total_repos,
                )
        except Exception:
            logger.exception("Scheduled update check failed")
            self._last_run_time = start_time

    # ── Manual Trigger ───────────────────────────────────────────────────────

    async def check_now(self) -> UpdateReport:
        """Run an immediate update check (not via the scheduler).

        Returns:
            The UpdateReport for this check.
        """
        logger.info("Manual update check triggered")
        return await self._checker.check_all()

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get the current manager status.

        Returns:
            A dictionary with running state, next scheduled run time, last
            run time, and the last report summary.
        """
        job = self._scheduler.get_job(self._JOB_ID)
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None

        return {
            "running": self._running,
            "check_interval_hours": self._check_interval_hours,
            "next_scheduled_run": next_run,
            "last_run_time": (
                self._last_run_time.isoformat()
                if self._last_run_time
                else None
            ),
            "last_report": (
                {
                    "checked_at": self._last_report.checked_at.isoformat(),
                    "total_repos": self._last_report.total_repos,
                    "repos_with_updates": self._last_report.repos_with_updates,
                    "results": [
                        {
                            "repo": r.repo_name,
                            "has_updates": r.has_updates,
                            "commits_behind": r.commits_behind,
                            "latest_tag": r.latest_tag,
                            "error": r.error,
                        }
                        for r in self._last_report.results
                    ],
                }
                if self._last_report
                else None
            ),
        }

    @property
    def last_report(self) -> Optional[UpdateReport]:
        """The most recent UpdateReport from a scheduled check."""
        return self._last_report