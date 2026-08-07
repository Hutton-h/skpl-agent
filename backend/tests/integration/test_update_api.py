"""Tests for update API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/updates/status")
    async def update_status():
        return {
            "repos": [
                {
                    "name": "agentscope",
                    "url": "https://github.com/agentscope-ai/agentscope",
                    "branch": "main",
                    "has_updates": False,
                    "latest_commit": "abc123",
                    "commits_behind": 0,
                    "checked_at": "2026-07-27T00:00:00Z",
                },
                {
                    "name": "openwolf",
                    "url": "https://github.com/nicklausroach/OpenWolf",
                    "branch": "main",
                    "has_updates": True,
                    "latest_commit": "def456",
                    "commits_behind": 3,
                    "checked_at": "2026-07-27T00:00:00Z",
                },
            ],
            "total_repos": 2,
            "repos_with_updates": 1,
            "checked_at": "2026-07-27T00:00:00Z",
        }

    @app.post("/api/updates/check")
    async def trigger_check():
        return {"status": "check_initiated"}

    @app.get("/api/updates/repo/{repo_name}")
    async def repo_status(repo_name: str):
        if repo_name == "agentscope":
            return {
                "name": "agentscope",
                "has_updates": False,
            }
        return {"error": "not found"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestUpdateAPI:
    """Integration tests for update API endpoints."""

    def test_get_status(self, client: TestClient) -> None:
        """Status endpoint returns all repos."""
        response = client.get("/api/updates/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_repos"] == 2
        assert data["repos_with_updates"] == 1

    def test_status_has_repo_details(self, client: TestClient) -> None:
        """Status includes per-repo details."""
        response = client.get("/api/updates/status")
        data = response.json()
        assert len(data["repos"]) == 2
        assert data["repos"][0]["name"] == "agentscope"
        assert data["repos"][1]["has_updates"] is True

    def test_trigger_check(self, client: TestClient) -> None:
        """Trigger check endpoint initiates a check."""
        response = client.post("/api/updates/check")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "check_initiated"

    def test_get_repo_status(self, client: TestClient) -> None:
        """Repo status endpoint returns specific repo."""
        response = client.get("/api/updates/repo/agentscope")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "agentscope"

    def test_get_repo_not_found(self, client: TestClient) -> None:
        """Unknown repo returns error."""
        response = client.get("/api/updates/repo/unknown")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_status_response_format(self, client: TestClient) -> None:
        """Status response has correct format."""
        response = client.get("/api/updates/status")
        data = response.json()
        for repo in data["repos"]:
            assert "name" in repo
            assert "has_updates" in repo
            assert "checked_at" in repo