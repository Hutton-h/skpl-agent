"""Tests for update checker."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from skpl_agent.updates import UpdateService


class TestUpdateService:
    """Tests for UpdateService."""

    @pytest.fixture
    def sources_config(self) -> dict:
        return {
            "repos": [
                {
                    "name": "agentscope",
                    "url": "https://github.com/agentscope-ai/agentscope",
                    "branch": "main",
                    "enabled": True,
                },
                {
                    "name": "openwolf",
                    "url": "https://github.com/nicklausroach/OpenWolf",
                    "branch": "main",
                    "enabled": True,
                },
                {
                    "name": "disabled-repo",
                    "url": "https://github.com/example/disabled",
                    "branch": "main",
                    "enabled": False,
                },
            ],
            "check_interval_hours": 6,
            "auto_merge": False,
            "notify_on_update": True,
        }

    @pytest.fixture
    def sources_file(self, sources_config: dict) -> Path:
        """Create a temporary sources.json file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(sources_config, f)
        return Path(f.name)

    def test_load_sources(self, sources_file: Path) -> None:
        """UpdateService loads sources from config."""
        service = UpdateService(sources_path=sources_file)
        assert len(service.sources) == 3
        assert service.sources[0]["name"] == "agentscope"

    def test_disabled_repos_excluded(self, sources_file: Path) -> None:
        """Disabled repos are not checked."""
        service = UpdateService(sources_path=sources_file)
        enabled = [r for r in service.sources if r.get("enabled", True)]
        assert len(enabled) == 2

    @pytest.mark.asyncio
    async def test_check_now_empty(self, sources_file: Path) -> None:
        """check_now returns report with no updates initially."""
        service = UpdateService(sources_path=sources_file)
        with patch.object(service, "_check_repo") as mock_check:
            mock_check.return_value = {
                "name": "agentscope",
                "has_updates": False,
                "latest_commit": "abc123",
                "commits_behind": 0,
            }
            report = await service.check_now()
            assert report.total_repos == 2  # Only enabled repos
            assert report.repos_with_updates == 0

    @pytest.mark.asyncio
    async def test_check_now_with_updates(self, sources_file: Path) -> None:
        """check_now detects updates."""
        service = UpdateService(sources_path=sources_file)

        async def mock_check(repo):
            return {
                "name": repo["name"],
                "has_updates": repo["name"] == "agentscope",
                "latest_commit": "new123",
                "commits_behind": 5 if repo["name"] == "agentscope" else 0,
            }

        service._check_repo = mock_check
        report = await service.check_now()
        assert report.repos_with_updates == 1

    def test_get_repo_by_name(self, sources_file: Path) -> None:
        """get_repo returns specific repo by name."""
        service = UpdateService(sources_path=sources_file)
        repo = service.get_repo("agentscope")
        assert repo is not None
        assert repo["url"] == "https://github.com/agentscope-ai/agentscope"

    def test_get_repo_not_found(self, sources_file: Path) -> None:
        """get_repo returns None for unknown repo."""
        service = UpdateService(sources_path=sources_file)
        assert service.get_repo("nonexistent") is None

    def test_intervals(self, sources_file: Path) -> None:
        """Check interval is read from config."""
        service = UpdateService(sources_path=sources_file)
        assert service.check_interval_hours == 6


class TestUpdateReport:
    """Tests for update report data structures."""

    def test_empty_report(self) -> None:
        """Empty report has no updates."""
        from skpl_agent.updates import UpdateReport
        report = UpdateReport()
        assert report.has_any_updates is False
        assert report.repos_with_updates == 0

    def test_report_with_updates(self) -> None:
        """Report with updates shows correctly."""
        from skpl_agent.updates import RepoStatus, UpdateReport

        status = RepoStatus(
            name="test-repo",
            url="https://github.com/test/repo",
            branch="main",
            enabled=True,
            has_updates=True,
            commits_behind=3,
        )
        report = UpdateReport()
        report.repos.append(status)
        report.repos_with_updates = 1
        assert report.has_any_updates is True