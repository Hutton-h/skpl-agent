#!/usr/bin/env python3
"""Update checker — CLI script to check for upstream project updates.

Checks the configured upstream repositories (AgentScope, OpenWolf, Agent-S,
Firecrawl) for new commits, releases, or tags since the last recorded check.

Usage:
    python backend/scripts/update_checker.py              # Check all repos
    python backend/scripts/update_checker.py --repo agentscope  # Check specific repo
    python backend/scripts/update_checker.py --json       # Output as JSON
    python backend/scripts/update_checker.py --github-issue  # Create GitHub Issue if updates found

Configuration is read from backend/src/skpl_agent/updates/sources.json.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "backend" / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("update_checker")


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class RepoStatus:
    """Status of a single upstream repository."""

    name: str
    url: str
    branch: str
    enabled: bool
    last_known_commit: str | None = None
    latest_commit: str | None = None
    latest_tag: str | None = None
    commits_behind: int = 0
    has_updates: bool = False
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None


@dataclass
class UpdateReport:
    """Aggregated update check report."""

    repos: list[RepoStatus] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_repos: int = 0
    repos_with_updates: int = 0
    total_commits_behind: int = 0

    @property
    def has_any_updates(self) -> bool:
        return self.repos_with_updates > 0


# ---------------------------------------------------------------------------
# State File
# ---------------------------------------------------------------------------


class StateManager:
    """Manages persistent state of last-known commits for each repo."""

    def __init__(self, state_path: Path | None = None) -> None:
        if state_path is None:
            state_path = _project_root / ".skpl" / "update_state.json"
        self._state_path = state_path
        self._state: dict[str, dict[str, str]] = {}

    def load(self) -> dict[str, dict[str, str]]:
        """Load state from disk."""
        if self._state_path.exists():
            try:
                self._state = json.loads(self._state_path.read_text(encoding="utf-8"))
                logger.debug("Loaded state from %s", self._state_path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load state: %s", exc)
                self._state = {}
        return self._state

    def save(self) -> None:
        """Save state to disk."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(self._state, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.debug("Saved state to %s", self._state_path)

    def get_commit(self, repo_name: str) -> str | None:
        return self._state.get(repo_name, {}).get("commit")

    def set_commit(self, repo_name: str, commit: str) -> None:
        self._state.setdefault(repo_name, {})["commit"] = commit
        self._state[repo_name]["checked_at"] = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Load Configuration
# ---------------------------------------------------------------------------


def load_sources() -> list[dict]:
    """Load upstream repository sources from sources.json."""
    sources_path = (
        _project_root / "backend" / "src" / "skpl_agent" / "updates" / "sources.json"
    )
    if not sources_path.exists():
        logger.error("sources.json not found at %s", sources_path)
        return []

    try:
        data = json.loads(sources_path.read_text(encoding="utf-8"))
        return data.get("repos", [])
    except Exception as exc:
        logger.error("Failed to load sources.json: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Git Operations
# ---------------------------------------------------------------------------


def _run_git(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "git not found in PATH"


def get_latest_commit(repo_url: str, branch: str) -> str | None:
    """Get the latest commit hash from a remote repository."""
    returncode, stdout, stderr = _run_git(
        ["ls-remote", repo_url, f"refs/heads/{branch}"],
    )
    if returncode != 0:
        logger.warning("Failed to get latest commit for %s: %s", repo_url, stderr)
        return None
    if not stdout:
        return None
    return stdout.split()[0]


def get_latest_tag(repo_url: str) -> str | None:
    """Get the latest tag from a remote repository."""
    returncode, stdout, stderr = _run_git(
        ["ls-remote", "--tags", "--sort=-version:refname", repo_url],
    )
    if returncode != 0:
        logger.warning("Failed to get tags for %s: %s", repo_url, stderr)
        return None
    if not stdout:
        return None
    # Get the most recent tag, excluding ^{} dereferences
    for line in stdout.splitlines():
        if "^{}" not in line:
            tag = line.split("refs/tags/")[-1]
            return tag
    return None


def count_commits_behind(repo_url: str, branch: str, since_commit: str) -> int | None:
    """Count how many commits are ahead of a known commit."""
    # Clone to temp dir and count
    returncode, stdout, stderr = _run_git(
        ["ls-remote", repo_url, f"refs/heads/{branch}"],
    )
    if returncode != 0:
        return None

    # We can't easily count without a local clone, so estimate from refs
    # For a more accurate count, use GitHub API
    return None  # Requires GitHub API or local clone


# ---------------------------------------------------------------------------
# Check Logic
# ---------------------------------------------------------------------------


def check_repo(repo_config: dict, state: StateManager) -> RepoStatus:
    """Check a single repository for updates."""
    name = repo_config.get("name", "unknown")
    url = repo_config.get("url", "")
    branch = repo_config.get("branch", "main")
    enabled = repo_config.get("enabled", True)

    status = RepoStatus(
        name=name,
        url=url,
        branch=branch,
        enabled=enabled,
    )

    if not enabled:
        return status

    try:
        last_commit = state.get_commit(name)
        status.last_known_commit = last_commit

        latest_commit = get_latest_commit(url, branch)
        status.latest_commit = latest_commit

        latest_tag = get_latest_tag(url)
        status.latest_tag = latest_tag

        if latest_commit and last_commit and latest_commit != last_commit:
            status.has_updates = True
            logger.info(
                "%s: NEW commits detected! %s → %s", name, last_commit[:8], latest_commit[:8],
            )
        elif latest_commit:
            logger.info(
                "%s: Up to date (commit: %s)", name, latest_commit[:8],
            )
            # Update state even if no changes (first run)
            if not last_commit:
                state.set_commit(name, latest_commit)

        # Try to get commit count behind via GitHub API if available
        if latest_commit and last_commit and latest_commit != last_commit:
            behind = count_commits_behind(url, branch, last_commit)
            if behind is not None:
                status.commits_behind = behind

    except Exception as exc:
        status.error = str(exc)
        logger.error("Error checking %s: %s", name, exc)

    return status


def check_all(repos: list[dict], state: StateManager) -> UpdateReport:
    """Check all configured repositories."""
    report = UpdateReport()
    report.total_repos = len(repos)

    for repo_config in repos:
        status = check_repo(repo_config, state)
        report.repos.append(status)

        if status.has_updates:
            report.repos_with_updates += 1
            report.total_commits_behind += status.commits_behind

        # Update state for next check
        if status.latest_commit and not status.error:
            state.set_commit(status.name, status.latest_commit)

    return report


# ---------------------------------------------------------------------------
# Output Formatters
# ---------------------------------------------------------------------------


def format_text(report: UpdateReport) -> str:
    """Format report as human-readable text."""
    lines = [
        f"SKPL Agent — Upstream Update Check",
        f"Checked at: {report.checked_at}",
        f"",
        f"Repositories checked: {report.total_repos}",
        f"Updates available: {report.repos_with_updates}",
        f"",
    ]

    for repo in report.repos:
        status_icon = "⚠" if repo.has_updates else "✓"
        lines.append(f"  {status_icon} {repo.name} ({repo.branch})")

        if not repo.enabled:
            lines.append(f"    Status: disabled")
            continue

        if repo.error:
            lines.append(f"    Error: {repo.error}")
            continue

        if repo.latest_commit:
            lines.append(f"    Latest commit: {repo.latest_commit[:8]}")
        if repo.latest_tag:
            lines.append(f"    Latest tag: {repo.latest_tag}")
        if repo.has_updates:
            lines.append(f"    *** UPDATES AVAILABLE ***")
            if repo.commits_behind > 0:
                lines.append(f"    Commits behind: {repo.commits_behind}")

    if report.repos_with_updates > 0:
        lines.append(f"")
        lines.append(f"Run 'make check-updates' for details or check GitHub Actions.")

    return "\n".join(lines)


def format_json(report: UpdateReport) -> str:
    """Format report as JSON."""
    return json.dumps({
        "checked_at": report.checked_at,
        "total_repos": report.total_repos,
        "repos_with_updates": report.repos_with_updates,
        "total_commits_behind": report.total_commits_behind,
        "repos": [
            {
                "name": r.name,
                "url": r.url,
                "branch": r.branch,
                "enabled": r.enabled,
                "last_known_commit": r.last_known_commit,
                "latest_commit": r.latest_commit,
                "latest_tag": r.latest_tag,
                "commits_behind": r.commits_behind,
                "has_updates": r.has_updates,
                "checked_at": r.checked_at,
                "error": r.error,
            }
            for r in report.repos
        ],
    }, indent=2)


def format_github_issue(report: UpdateReport) -> str:
    """Format report as a GitHub Issue body."""
    lines = [
        "## Upstream Update Check",
        "",
        f"**Checked at:** {report.checked_at}",
        f"**Repositories with updates:** {report.repos_with_updates}/{report.total_repos}",
        "",
    ]

    if report.repos_with_updates == 0:
        lines.append("No updates detected. All repositories are up to date.")
        return "\n".join(lines)

    lines.append("### Repositories with Updates")
    lines.append("")

    for repo in report.repos:
        if not repo.has_updates:
            continue
        lines.append(f"#### {repo.name}")
        lines.append(f"- **URL:** {repo.url}")
        lines.append(f"- **Branch:** {repo.branch}")
        if repo.last_known_commit and repo.latest_commit:
            lines.append(f"- **Previous commit:** `{repo.last_known_commit[:8]}`")
            lines.append(f"- **Latest commit:** `{repo.latest_commit[:8]}`")
        if repo.latest_tag:
            lines.append(f"- **Latest tag:** {repo.latest_tag}")
        if repo.commits_behind > 0:
            lines.append(f"- **Commits behind:** {repo.commits_behind}")
        lines.append("")

    lines.append("---")
    lines.append("_Auto-generated by SKPL Agent update checker_")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run the update checker."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check upstream projects for updates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo", type=str, default=None,
        help="Check only a specific repository (by name)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--github-issue", action="store_true",
        help="Output in GitHub Issue markdown format",
    )
    parser.add_argument(
        "--state-file", type=str, default=None,
        help="Path to state file (default: .skpl/update_state.json)",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Do not save state after checking",
    )
    args = parser.parse_args()

    state_path = Path(args.state_file) if args.state_file else None
    state = StateManager(state_path)
    state.load()

    repos = load_sources()
    if not repos:
        logger.error("No repositories configured in sources.json")
        return 1

    if args.repo:
        repos = [r for r in repos if r.get("name") == args.repo]
        if not repos:
            logger.error("Repository '%s' not found in sources.json", args.repo)
            return 1

    report = check_all(repos, state)

    if not args.no_save:
        state.save()

    if args.github_issue:
        print(format_github_issue(report))
    elif args.json:
        print(format_json(report))
    else:
        print(format_text(report))

    return 0 if not report.has_any_updates else 1


if __name__ == "__main__":
    sys.exit(main())