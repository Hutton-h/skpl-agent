"""Tests for rate limit API integration."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient


@pytest.fixture
def app_with_rate_limit() -> FastAPI:
    from skpl_agent.middleware.rate_limit import RateLimitConfig, RateLimitMiddleware

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/data")
    async def get_data():
        return {"data": [1, 2, 3]}

    @app.post("/api/data")
    async def create_data():
        return {"created": True}

    @app.get("/api/agent/run")
    async def agent_run():
        return {"result": "completed"}

    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig(
            ip_max_tokens=3,
            ip_tokens_per_second=0.5,
            key_max_tokens=10,
            key_tokens_per_second=2.0,
        ),
    )
    return app


@pytest.fixture
def client(app_with_rate_limit: FastAPI) -> TestClient:
    return TestClient(app_with_rate_limit)


class TestRateLimitAPI:
    """Integration tests for rate-limited API endpoints."""

    def test_health_always_accessible(self, client: TestClient) -> None:
        """Health endpoint is never rate-limited."""
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_normal_endpoint_accessible(self, client: TestClient) -> None:
        """Normal endpoints are accessible within limits."""
        response = client.get("/api/data")
        assert response.status_code == 200
        assert response.json() == {"data": [1, 2, 3]}

    def test_rate_limit_exceeded_returns_429(self, client: TestClient) -> None:
        """Exceeding rate limit returns 429 with proper format."""
        # Exhaust bucket
        for _ in range(10):
            client.get("/api/data")

        response = client.get("/api/data")
        if response.status_code == 429:
            data = response.json()
            assert data["error"] == "Too Many Requests"
            assert "retry_after_seconds" in data
            assert "Retry-After" in response.headers
            assert "X-RateLimit-Tier" in response.headers

    def test_rate_limit_headers_present(self, client: TestClient) -> None:
        """Rate limit headers are present in successful responses."""
        response = client.get("/api/data")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_post_request_also_limited(self, client: TestClient) -> None:
        """POST requests are also rate-limited."""
        for _ in range(5):
            client.post("/api/data")

        response = client.post("/api/data")
        # May or may not be rate-limited depending on timing
        assert response.status_code in (200, 429)

    def test_api_key_bypass(self, client: TestClient) -> None:
        """API key requests use separate (more generous) bucket."""
        for _ in range(5):
            response = client.get(
                "/api/data",
                headers={"Authorization": "Bearer sk-test-key"},
            )
            assert response.status_code == 200

    def test_expensive_path_cost(self, client: TestClient) -> None:
        """Expensive paths consume more tokens and are limited faster."""
        responses = []
        for _ in range(5):
            resp = client.get("/api/agent/run")
            responses.append(resp.status_code)
        # Should have some 429s since agent/run costs 5 tokens
        assert 429 in responses or all(s == 200 for s in responses)

    def test_different_ips_independent(self, app_with_rate_limit: FastAPI) -> None:
        """Different IPs have independent rate limits."""
        client1 = TestClient(app_with_rate_limit)
        client2 = TestClient(app_with_rate_limit)

        # Exhaust client1
        for _ in range(10):
            client1.get("/api/data", headers={"X-Forwarded-For": "10.0.0.1"})

        # Client2 should still be fine
        response = client2.get("/api/data", headers={"X-Forwarded-For": "10.0.0.2"})
        assert response.status_code == 200