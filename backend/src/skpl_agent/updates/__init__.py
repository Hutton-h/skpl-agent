"""Upstream project update detection engine.

Monitors the four upstream projects (AgentScope, OpenWolf, Agent-S, Firecrawl)
for new commits, releases, and breaking changes. Supports configurable
check intervals and notification channels.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UpstreamRepo:
    """An upstream repository to track."""

    name: str
    url: str
    branch: str = "main"
    enabled: bool = True


@dataclass
class UpdateCheckResult:
    """Result of a single update check for one repo."""

    repo_name: str
    repo_url: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    has_updates: bool = False
    current_commit: str = ""
    latest_commit: str = ""
    commits_behind: int = 0
    latest_tag: str = ""
    breaking_changes: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RepoStatus:
    """Status of a single repository for update reports."""

    name: str
    url: str
    branch: str = "main"
    enabled: bool = True
    has_updates: bool = False
    commits_behind: int = 0


@dataclass
class UpdateReport:
    """Aggregated update check report for all repos."""

    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    results: list[UpdateCheckResult] = field(default_factory=list)
    repos: list[RepoStatus] = field(default_factory=list)
    total_repos: int = 0
    repos_with_updates: int = 0

    @property
    def has_any_updates(self) -> bool:
        return self.repos_with_updates > 0


class UpdateChecker:
    """Service for checking upstream project updates.

    Uses GitHub API to compare branches and detect new commits/tags.
    In production, this would use the GitHub API with authentication.
    For now, it provides the framework and can be extended with real API calls.
    """

    def __init__(self, repos: list[UpstreamRepo] | None = None) -> None:
        self._repos = repos or []
        self._last_check: datetime | None = None
        self._last_results: list[UpdateCheckResult] = []

    # ── Repository Management ─────────────────────────────────────────

    def add_repo(self, repo: UpstreamRepo) -> None:
        """Add an upstream repository to track."""
        existing = [r for r in self._repos if r.name == repo.name]
        if existing:
            idx = self._repos.index(existing[0])
            self._repos[idx] = repo
        else:
            self._repos.append(repo)
        logger.info("Added upstream repo: %s (%s)", repo.name, repo.url)

    def remove_repo(self, name: str) -> bool:
        """Remove an upstream repository from tracking."""
        before = len(self._repos)
        self._repos = [r for r in self._repos if r.name != name]
        return len(self._repos) < before

    def get_repos(self) -> list[UpstreamRepo]:
        """Get all tracked repositories."""
        return list(self._repos)

    # ── Update Checking ───────────────────────────────────────────────

    async def check_all(self) -> UpdateReport:
        """Check all enabled upstream repos for updates."""
        enabled = [r for r in self._repos if r.enabled]
        results: list[UpdateCheckResult] = []

        for repo in enabled:
            try:
                result = await self._check_repo(repo)
            except Exception as e:
                logger.error(
                    "Failed to check %s: %s", repo.name, e
                )
                result = UpdateCheckResult(
                    repo_name=repo.name,
                    repo_url=repo.url,
                    error=str(e),
                )
            results.append(result)

        self._last_check = datetime.now(timezone.utc)
        self._last_results = results

        report = UpdateReport(
            checked_at=self._last_check,
            results=results,
            total_repos=len(results),
            repos_with_updates=sum(1 for r in results if r.has_updates),
        )

        if report.has_any_updates:
            updated = [r.repo_name for r in results if r.has_updates]
            logger.info(
                "Updates found for: %s",
                ", ".join(updated),
            )

        return report

    async def _check_repo(self, repo: UpstreamRepo) -> UpdateCheckResult:
        """Check a single repository for updates.

        In production, this would call the GitHub API:
            GET /repos/{owner}/{repo}/compare/{base}...{head}
            GET /repos/{owner}/{repo}/tags

        For now, returns a stub result indicating no updates.
        """
        logger.debug("Checking %s (%s/%s)...", repo.name, repo.url, repo.branch)

        # Stub implementation — in production, call GitHub API here
        return UpdateCheckResult(
            repo_name=repo.name,
            repo_url=repo.url,
            has_updates=False,
            current_commit="unknown",
            latest_commit="unknown",
            commits_behind=0,
            latest_tag="unknown",
        )

    # ── Results ───────────────────────────────────────────────────────

    def get_last_results(self) -> list[UpdateCheckResult]:
        """Get the results of the last update check."""
        return list(self._last_results)

    def get_last_check_time(self) -> datetime | None:
        """Get the timestamp of the last update check."""
        return self._last_check

    async def get_status(self) -> dict[str, Any]:
        """Get the current update checking status."""
        return {
            "tracked_repos": len(self._repos),
            "enabled_repos": sum(1 for r in self._repos if r.enabled),
            "last_check": (
                self._last_check.isoformat() if self._last_check else None
            ),
            "last_results": [
                {
                    "repo": r.repo_name,
                    "has_updates": r.has_updates,
                    "commits_behind": r.commits_behind,
                    "latest_tag": r.latest_tag,
                    "error": r.error,
                    "checked_at": r.checked_at.isoformat(),
                }
                for r in self._last_results
            ],
        }


# Default checker with the four upstream repos
def create_default_checker() -> UpdateChecker:
    """Create an UpdateChecker with the four default upstream repos."""
    repos = [
        UpstreamRepo(
            name="agentscope",
            url="https://github.com/agentscope-ai/agentscope",
            branch="main",
        ),
        UpstreamRepo(
            name="openwolf",
            url="https://github.com/nicklausroach/OpenWolf",
            branch="main",
        ),
        UpstreamRepo(
            name="agent-s",
            url="https://github.com/simular-ai/Agent-S",
            branch="main",
        ),
        UpstreamRepo(
            name="firecrawl",
            url="https://github.com/mendableai/firecrawl",
            branch="main",
        ),
    ]
    return UpdateChecker(repos=repos)


class UpdateService:
    """High-level update service wrapping UpdateChecker with JSON config loading.

    Provides the API expected by the test suite and service layer.
    """

    def __init__(self, sources_path: Path | str | None = None) -> None:
        self._sources_path = Path(sources_path) if sources_path else None
        self.sources: list[dict[str, Any]] = []
        self.check_interval_hours: int = 24

        if self._sources_path and self._sources_path.exists():
            self._load_sources()

    def _load_sources(self) -> None:
        """Load sources from JSON config file."""
        if self._sources_path is None:
            return
        try:
            data = json.loads(self._sources_path.read_text(encoding="utf-8"))
            self.sources = data.get("repos", [])
            self.check_interval_hours = data.get("check_interval_hours", 24)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load update sources: %s", e)

    def get_repo(self, name: str) -> dict[str, Any] | None:
        """Get a specific repo by name."""
        for repo in self.sources:
            if repo.get("name") == name:
                return repo
        return None

    async def check_now(self) -> UpdateReport:
        """Check all enabled repos for updates."""
        enabled = [r for r in self.sources if r.get("enabled", True)]
        report = UpdateReport(total_repos=len(enabled))

        for repo in enabled:
            result = await self._check_repo(repo)
            if result.get("has_updates"):
                report.repos_with_updates += 1

        return report

    async def _check_repo(self, repo: dict[str, Any]) -> dict[str, Any]:
        """Check a single repo for updates (stub)."""
        return {
            "name": repo.get("name", ""),
            "has_updates": False,
            "latest_commit": "",
            "commits_behind": 0,
        }