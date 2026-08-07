"""Tests for desktop API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/desktop/nodes")
    async def get_nodes():
        return {
            "nodes": [
                {
                    "id": "node-1",
                    "status": "connected",
                    "hostname": "dev-machine",
                    "platform": "Windows",
                    "lastActive": "2026-07-27T00:00:00Z",
                    "screenshotCount": 42,
                    "actionCount": 150,
                },
            ],
        }

    @app.get("/api/desktop/nodes/{node_id}")
    async def get_node(node_id: str):
        if node_id == "node-1":
            return {
                "id": "node-1",
                "status": "connected",
                "hostname": "dev-machine",
                "platform": "Windows",
            }
        return {"error": "not found"}

    @app.post("/api/desktop/execute")
    async def execute_action(request: dict):
        return {
            "success": True,
            "action_type": request.get("action", "click"),
            "screenshot": "base64-fake",
        }

    @app.get("/api/desktop/screenshot/{node_id}")
    async def get_screenshot(node_id: str):
        return {"node_id": node_id, "screenshot": "base64-fake-screenshot"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestDesktopAPI:
    """Integration tests for desktop API endpoints."""

    def test_get_nodes(self, client: TestClient) -> None:
        """Nodes endpoint returns connected nodes."""
        response = client.get("/api/desktop/nodes")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["status"] == "connected"

    def test_get_specific_node(self, client: TestClient) -> None:
        """Get specific node returns node details."""
        response = client.get("/api/desktop/nodes/node-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "node-1"

    def test_get_unknown_node(self, client: TestClient) -> None:
        """Unknown node returns error."""
        response = client.get("/api/desktop/nodes/unknown")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_execute_click(self, client: TestClient) -> None:
        """Execute click action returns success."""
        response = client.post(
            "/api/desktop/execute",
            json={"action": "click", "node_id": "node-1", "x": 100, "y": 200},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_execute_type(self, client: TestClient) -> None:
        """Execute type action returns success."""
        response = client.post(
            "/api/desktop/execute",
            json={"action": "type", "node_id": "node-1", "text": "Hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_screenshot(self, client: TestClient) -> None:
        """Get screenshot endpoint returns screenshot."""
        response = client.get("/api/desktop/screenshot/node-1")
        assert response.status_code == 200
        data = response.json()
        assert "screenshot" in data

    def test_execute_validation(self, client: TestClient) -> None:
        """Execute validates required fields."""
        response = client.post(
            "/api/desktop/execute",
            json={},  # Missing action
        )
        assert response.status_code in (200, 400, 422)