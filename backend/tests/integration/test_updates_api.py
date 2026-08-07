"""Integration tests for Updates API routes.

Tests cover:
- GET /api/updates/status — get update service status
- GET /api/updates/health — health check
- POST /api/updates/check — trigger update check
- POST /api/updates/merge/{repo_name} — merge repo
- POST /api/updates/rollback/{repo_name} — rollback repo
- GET /api/updates/repos — list repos
- POST /api/updates/repos — add repo
- DELETE /api/updates/repos/{name} — remove repo
- Error paths: 400, 404, 500
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skpl_agent.updates import UpdateReport, UpdateCheckResult, UpstreamRepo


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> MagicMock:
    """Create a mock UpdateService."""
    svc = MagicMock()
    svc.get_status = AsyncMock(return_value={
        "running": True,
        "check_interval_hours": 6,
        "auto_merge": False,
        "last_check": "2024-01-01T00:00:00",
        "last_report": {
            "total_repos": 4,
            "repos_with_updates": 1,
            "results": [
                {
                    "repo": "agentscope",
                    "has_updates": True,
                    "commits_behind": 3,
                    "latest_tag": "v2.0.0",
                    "breaking_changes": [],
                    "error": None,
                },
            ],
        },
        "checker": {
            "tracked_repos": 4,
            "enabled_repos": 4,
            "last_check": "2024-01-01T00:00:00",
            "last_results": [],
        },
        "merge_history": [],
    })
    svc.check_now = AsyncMock(return_value=UpdateReport(
        total_repos=4,
        repos_with_updates=0,
        results=[],
    ))
    svc.merge_repo = AsyncMock(return_value=MagicMock(
        repo_name="agentscope",
        status="merged",
        files_changed=5,
        files_added=2,
        files_deleted=1,
        conflicts=[],
        merged_at=MagicMock(),
    ))
    svc.rollback_repo = AsyncMock(return_value=True)
    svc.add_repo = AsyncMock()
    svc.remove_repo = AsyncMock(return_value=True)
    svc.list_repos = AsyncMock(return_value=[
        {"name": "agentscope", "url": "https://github.com/agentscope-ai/agentscope", "branch": "main", "enabled": True},
        {"name": "openwolf", "url": "https://github.com/nicklausroach/OpenWolf", "branch": "main", "enabled": True},
    ])
    return svc


@pytest.fixture
def client(mock_service: MagicMock) -> TestClient:
    """Create a FastAPI TestClient with mocked Update service."""
    from skpl_agent.updates import router as updates_router

    with patch.object(
        updates_router, "get_update_service", return_value=mock_service
    ):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(updates_router.router)
        return TestClient(app)


# ── Status Endpoint Tests ──────────────────────────────────────────────────


class TestStatusEndpoint:
    """Tests for GET /api/updates/status."""

    def test_get_status(self, client: TestClient) -> None:
        """Getting status returns service status."""
        response = client.get("/api/updates/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert data["check_interval_hours"] == 6
        assert data["auto_merge"] is False
        assert "last_check" in data
        assert "checker" in data
        assert "merge_history" in data


# ── Health Endpoint Tests ──────────────────────────────────────────────────


class TestHealthEndpoint:
    """Tests for GET /api/updates/health."""

    def test_health_check(self, client: TestClient) -> None:
        """Health check returns ok status."""
        response = client.get("/api/updates/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["component"] == "updates"


# ── Check Endpoint Tests ───────────────────────────────────────────────────


class TestCheckEndpoint:
    """Tests for POST /api/updates/check."""

    def test_check_now(self, client: TestClient) -> None:
        """Triggering check returns report."""
        response = client.post("/api/updates/check")
        assert response.status_code == 200
        data = response.json()
        assert "checked_at" in data
        assert data["total_repos"] == 4
        assert data["repos_with_updates"] == 0
        assert "results" in data


# ── Merge Endpoint Tests ───────────────────────────────────────────────────


class TestMergeEndpoint:
    """Tests for POST /api/updates/merge/{repo_name}."""

    def test_merge_repo_success(self, client: TestClient) -> None:
        """Merging a repo returns merge result."""
        response = client.post("/api/updates/merge/agentscope")
        assert response.status_code == 200
        data = response.json()
        assert data["repo_name"] == "agentscope"
        assert data["status"] == "merged"
        assert data["files_changed"] == 5
        assert data["files_added"] == 2
        assert data["files_deleted"] == 1

    def test_merge_repo_failed(self, client: TestClient, mock_service: MagicMock) -> None:
        """Merging a repo that fails returns 500."""
        mock_result = MagicMock()
        mock_result.status = "failed"
        mock_result.error = "Merge conflict detected"
        mock_service.merge_repo.return_value = mock_result

        response = client.post("/api/updates/merge/problem-repo")
        assert response.status_code == 500
        assert "Merge conflict" in response.json()["detail"]


# ── Rollback Endpoint Tests ────────────────────────────────────────────────


class TestRollbackEndpoint:
    """Tests for POST /api/updates/rollback/{repo_name}."""

    def test_rollback_repo_success(self, client: TestClient) -> None:
        """Rolling back a repo returns success."""
        response = client.post("/api/updates/rollback/agentscope")
        assert response.status_code == 200
        data = response.json()
        assert data["repo_name"] == "agentscope"
        assert data["rolled_back"] is True

    def test_rollback_repo_failed(self, client: TestClient, mock_service: MagicMock) -> None:
        """Rolling back a repo that fails returns result."""
        mock_service.rollback_repo.return_value = False

        response = client.post("/api/updates/rollback/unknown-repo")
        assert response.status_code == 200
        data = response.json()
        assert data["rolled_back"] is False


# ── List Repos Endpoint Tests ──────────────────────────────────────────────


class TestListReposEndpoint:
    """Tests for GET /api/updates/repos."""

    def test_list_repos(self, client: TestClient) -> None:
        """Listing repos returns tracked repos."""
        response = client.get("/api/updates/repos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "agentscope"
        assert data[1]["name"] == "openwolf"


# ── Add Repo Endpoint Tests ────────────────────────────────────────────────


class TestAddRepoEndpoint:
    """Tests for POST /api/updates/repos."""

    def test_add_repo_success(self, client: TestClient) -> None:
        """Adding a repo returns success."""
        response = client.post("/api/updates/repos", json={
            "name": "new-repo",
            "url": "https://github.com/new/repo",
            "branch": "develop",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new-repo"
        assert data["url"] == "https://github.com/new/repo"
        assert data["branch"] == "develop"
        assert data["status"] == "added"

    def test_add_repo_missing_name(self, client: TestClient) -> None:
        """Adding a repo without name returns 400."""
        response = client.post("/api/updates/repos", json={
            "url": "https://github.com/new/repo",
        })
        assert response.status_code == 400
        assert "name" in response.json()["detail"].lower()

    def test_add_repo_missing_url(self, client: TestClient) -> None:
        """Adding a repo without url returns 400."""
        response = client.post("/api/updates/repos", json={
            "name": "new-repo",
        })
        assert response.status_code == 400
        assert "url" in response.json()["detail"].lower()

    def test_add_repo_default_branch(self, client: TestClient) -> None:
        """Adding a repo without branch defaults to main."""
        response = client.post("/api/updates/repos", json={
            "name": "new-repo",
            "url": "https://github.com/new/repo",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["branch"] == "main"


# ── Remove Repo Endpoint Tests ─────────────────────────────────────────────


class TestRemoveRepoEndpoint:
    """Tests for DELETE /api/updates/repos/{name}."""

    def test_remove_repo_success(self, client: TestClient) -> None:
        """Removing a repo returns success."""
        response = client.delete("/api/updates/repos/old-repo")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "old-repo"
        assert data["status"] == "removed"

    def test_remove_repo_not_found(self, client: TestClient, mock_service: MagicMock) -> None:
        """Removing a nonexistent repo returns 404."""
        mock_service.remove_repo.return_value = False

        response = client.delete("/api/updates/repos/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()