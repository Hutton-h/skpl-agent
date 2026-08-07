"""Update management service — scheduled checks and lifecycle management.

Provides:
- Scheduled update checking
- Automatic notification on updates
- Merge workflow orchestration
- Update history tracking
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from skpl_agent.updates import (
    UpdateChecker,
    UpdateReport,
    UpstreamRepo,
    create_default_checker,
)
from skpl_agent.updates.merger import UpdateMerger, MergeReport, MergeResult

logger = logging.getLogger(__name__)


class UpdateService:
    """Service for managing upstream update detection and merging.

    Handles the full update lifecycle:
    1. Periodic checking of upstream repos
    2. Notification of available updates
    3. Safe merge of non-conflicting changes
    4. Conflict reporting for manual review

    Usage:
        >>> service = UpdateService(check_interval_hours=6)
        >>> await service.start()
        >>> status = await service.get_status()
        >>> await service.check_now()
        >>> await service.stop()
    """

    def __init__(
        self,
        checker: Optional[UpdateChecker] = None,
        merger: Optional[UpdateMerger] = None,
        check_interval_hours: int = 6,
        auto_merge: bool = False,
        notify_on_update: bool = True,
        webhook_url: str = "",
    ) -> None:
        self._checker = checker or create_default_checker()
        self._merger = merger or UpdateMerger()
        self._check_interval = check_interval_hours * 3600
        self._auto_merge = auto_merge
        self._notify_on_update = notify_on_update
        self._webhook_url = webhook_url

        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._last_report: Optional[UpdateReport] = None
        self._merge_history: list[MergeResult] = []

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start periodic update checking."""
        if self._running:
            return
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info(
            "Update service started (interval=%dh, auto_merge=%s)",
            self._check_interval // 3600, self._auto_merge,
        )

    async def stop(self) -> None:
        """Stop periodic update checking."""
        self._running = False
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        self._check_task = None
        logger.info("Update service stopped")

    # ── Checking ─────────────────────────────────────────────────────────

    async def check_now(self) -> UpdateReport:
        """Run an immediate update check."""
        report = await self._checker.check_all()
        self._last_report = report

        if report.has_any_updates:
            updated = [r.repo_name for r in report.results if r.has_updates]
            logger.info("Updates available for: %s", ", ".join(updated))

            if self._notify_on_update:
                await self._notify(report)

            if self._auto_merge:
                for result in report.results:
                    if result.has_updates:
                        merge_result = await self._merger.merge(result.repo_name)
                        self._merge_history.append(merge_result)

        return report

    async def get_status(self) -> dict[str, Any]:
        """Get the current update service status."""
        checker_status = await self._checker.get_status()
        return {
            "running": self._running,
            "check_interval_hours": self._check_interval // 3600,
            "auto_merge": self._auto_merge,
            "last_check": (
                self._last_report.checked_at.isoformat()
                if self._last_report else None
            ),
            "last_report": (
                {
                    "total_repos": self._last_report.total_repos,
                    "repos_with_updates": self._last_report.repos_with_updates,
                    "results": [
                        {
                            "repo": r.repo_name,
                            "has_updates": r.has_updates,
                            "commits_behind": r.commits_behind,
                            "latest_tag": r.latest_tag,
                            "breaking_changes": r.breaking_changes,
                            "error": r.error,
                        }
                        for r in self._last_report.results
                    ],
                }
                if self._last_report else None
            ),
            "checker": checker_status,
            "merge_history": [
                {
                    "repo": m.repo_name,
                    "status": m.status,
                    "files_changed": m.files_changed,
                    "conflicts": m.conflicts,
                    "merged_at": m.merged_at.isoformat(),
                }
                for m in self._merge_history[-10:]  # Last 10
            ],
        }

    async def merge_repo(self, repo_name: str) -> MergeResult:
        """Manually trigger a merge for a specific repo."""
        result = await self._merger.merge(repo_name)
        self._merge_history.append(result)
        return result

    async def rollback_repo(self, repo_name: str) -> bool:
        """Rollback the last merge for a repo."""
        return await self._merger.rollback(repo_name)

    # ── Repo Management ──────────────────────────────────────────────────

    async def add_repo(self, name: str, url: str, branch: str = "main") -> None:
        """Add a new upstream repository to track."""
        repo = UpstreamRepo(name=name, url=url, branch=branch)
        self._checker.add_repo(repo)

    async def remove_repo(self, name: str) -> bool:
        """Remove an upstream repository from tracking."""
        return self._checker.remove_repo(name)

    async def list_repos(self) -> list[dict[str, Any]]:
        """List all tracked repositories."""
        return [
            {"name": r.name, "url": r.url, "branch": r.branch, "enabled": r.enabled}
            for r in self._checker.get_repos()
        ]

    # ── Internal ─────────────────────────────────────────────────────────

    async def _check_loop(self) -> None:
        """Periodic check loop."""
        while self._running:
            try:
                await self.check_now()
            except Exception as e:
                logger.error("Update check error: %s", e)
            await asyncio.sleep(self._check_interval)

    async def _notify(self, report: UpdateReport) -> None:
        """Send notifications about available updates."""
        if self._webhook_url:
            try:
                import aiohttp
                payload = {
                    "text": f"SKPL Agent: {report.repos_with_updates} repos have updates",
                    "report": {
                        "checked_at": report.checked_at.isoformat(),
                        "updates": [
                            {
                                "repo": r.repo_name,
                                "commits_behind": r.commits_behind,
                                "latest_tag": r.latest_tag,
                                "breaking_changes": r.breaking_changes,
                            }
                            for r in report.results if r.has_updates
                        ],
                    },
                }
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        self._webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10),
                    )
            except Exception as e:
                logger.error("Webhook notification failed: %s", e)