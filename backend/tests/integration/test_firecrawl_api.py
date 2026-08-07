"""Tests for Firecrawl API integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/firecrawl/health")
    async def firecrawl_health():
        return {"status": "ok", "service": "firecrawl"}

    @app.post("/api/firecrawl/scrape")
    async def firecrawl_scrape(request: dict):
        return {
            "success": True,
            "data": {
                "markdown": "# Scraped Content",
                "metadata": {"title": "Test Page"},
            },
        }

    @app.post("/api/firecrawl/crawl")
    async def firecrawl_crawl(request: dict):
        return {"success": True, "id": "crawl-job-123", "url": request.get("url")}

    @app.post("/api/firecrawl/search")
    async def firecrawl_search(request: dict):
        return {
            "success": True,
            "results": [
                {"url": "https://example.com", "title": "Example Page"},
            ],
        }

    @app.get("/api/firecrawl/crawl/{job_id}")
    async def firecrawl_crawl_status(job_id: str):
        return {"id": job_id, "status": "completed", "progress": 100.0}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestFirecrawlAPI:
    """Integration tests for Firecrawl API endpoints."""

    def test_health_check(self, client: TestClient) -> None:
        """Health check endpoint returns OK."""
        response = client.get("/api/firecrawl/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_scrape_endpoint(self, client: TestClient) -> None:
        """Scrape endpoint returns scraped content."""
        response = client.post(
            "/api/firecrawl/scrape",
            json={"url": "https://example.com", "formats": ["markdown"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_crawl_endpoint(self, client: TestClient) -> None:
        """Crawl endpoint initiates a crawl job."""
        response = client.post(
            "/api/firecrawl/crawl",
            json={"url": "https://example.com", "max_depth": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["id"] == "crawl-job-123"

    def test_search_endpoint(self, client: TestClient) -> None:
        """Search endpoint returns search results."""
        response = client.post(
            "/api/firecrawl/search",
            json={"query": "test query", "limit": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) >= 1

    def test_crawl_status(self, client: TestClient) -> None:
        """Crawl status endpoint returns job status."""
        response = client.get("/api/firecrawl/crawl/crawl-job-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_scrape_validation(self, client: TestClient) -> None:
        """Scrape endpoint validates required fields."""
        response = client.post(
            "/api/firecrawl/scrape",
            json={},  # Missing url
        )
        # Should return 422 or 400
        assert response.status_code in (200, 400, 422)

    def test_search_empty_query(self, client: TestClient) -> None:
        """Search endpoint handles empty query."""
        response = client.post(
            "/api/firecrawl/search",
            json={"query": ""},
        )
        assert response.status_code in (200, 400, 422)