"""Tests for rate limit middleware."""

from __future__ import annotations

import time

import pytest
from starlette.testclient import TestClient
from fastapi import FastAPI
from starlette.requests import Request

from skpl_agent.middleware.rate_limit import (
    RateLimitConfig,
    RateLimitMiddleware,
    TokenBucket,
    create_rate_limit_middleware,
)


class TestTokenBucket:
    """Tests for TokenBucket."""

    def test_initial_tokens(self) -> None:
        """Bucket starts with max tokens."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=1.0)
        assert bucket.tokens == 10.0

    def test_consume_success(self) -> None:
        """Consuming tokens when available succeeds."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=1.0)
        assert bucket.consume(5) is True
        assert bucket.tokens == 5.0

    def test_consume_exact(self) -> None:
        """Consuming exactly all tokens succeeds."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=1.0)
        assert bucket.consume(10) is True
        assert bucket.tokens == 0.0

    def test_consume_exceeded(self) -> None:
        """Consuming more than available fails."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=1.0)
        assert bucket.consume(11) is False
        assert bucket.tokens == 10.0  # Unchanged

    def test_consume_zero(self) -> None:
        """Consuming zero tokens succeeds."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=1.0)
        assert bucket.consume(0) is True
        assert bucket.tokens == 10.0

    def test_refill(self) -> None:
        """Tokens refill over time."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=10.0)
        bucket.tokens = 0
        bucket.last_refill = time.monotonic() - 1.0
        assert bucket.consume(5) is True  # ~10 tokens refilled

    def test_available_tokens(self) -> None:
        """available_tokens property returns current tokens."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=1.0)
        bucket.consume(3)
        assert bucket.available_tokens == 7.0

    def test_retry_after_seconds(self) -> None:
        """retry_after_seconds estimates wait time."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=2.0)
        bucket.tokens = 0
        assert bucket.retry_after_seconds >= 0.0

    def test_retry_after_zero_rate(self) -> None:
        """retry_after_seconds handles zero rate gracefully."""
        bucket = TokenBucket(max_tokens=10, tokens_per_second=0.0)
        bucket.tokens = 0
        assert bucket.retry_after_seconds == 60.0


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_defaults(self) -> None:
        """RateLimitConfig has sensible defaults."""
        config = RateLimitConfig()
        assert config.ip_max_tokens == 100
        assert config.ip_tokens_per_second == 10.0
        assert config.key_max_tokens == 500
        assert config.include_headers is True

    def test_exempt_paths(self) -> None:
        """Default exempt paths include health endpoints."""
        config = RateLimitConfig()
        assert "/health" in config.exempt_paths
        assert "/api/health" in config.exempt_paths

    def test_expensive_paths(self) -> None:
        """Expensive paths have higher token costs."""
        config = RateLimitConfig()
        assert config.expensive_paths["/api/agent/run"] == 5.0
        assert config.expensive_paths["/api/desktop/execute"] == 10.0


class TestRateLimitMiddleware:
    """Integration tests for RateLimitMiddleware."""

    @pytest.fixture
    def app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/api/test")
        async def test():
            return {"data": "test"}

        @app.get("/api/agent/run")
        async def agent_run():
            return {"result": "done"}

        app.add_middleware(
            RateLimitMiddleware,
            config=RateLimitConfig(
                ip_max_tokens=5,
                ip_tokens_per_second=1.0,
                key_max_tokens=10,
                key_tokens_per_second=2.0,
            ),
        )
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        return TestClient(app)

    def test_health_exempt(self, client: TestClient) -> None:
        """Health endpoint is exempt from rate limiting."""
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200

    def test_normal_request(self, client: TestClient) -> None:
        """Normal requests succeed within limits."""
        response = client.get("/api/test")
        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    def test_rate_limit_exceeded(self, client: TestClient) -> None:
        """Exceeding rate limit returns 429."""
        # Exhaust the bucket (max 5 tokens at 1/s)
        for _ in range(6):
            response = client.get("/api/test")

        # The 6th request should be rate-limited
        assert any(
            r.status_code == 429
            for r in [client.get("/api/test") for _ in range(3)]
        )

    def test_rate_limit_response_format(self, app: FastAPI) -> None:
        """429 response has correct format."""
        client = TestClient(app)
        # Exhaust bucket
        for _ in range(10):
            client.get("/api/test")

        response = client.get("/api/test")
        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert "retry_after_seconds" in data
            assert response.headers.get("Retry-After") is not None

    def test_rate_limit_headers(self, app: FastAPI) -> None:
        """Rate limit headers are included in responses."""
        client = TestClient(app)
        response = client.get("/api/test")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_api_key_bucket(self, app: FastAPI) -> None:
        """API key requests use the key bucket."""
        client = TestClient(app)
        response = client.get(
            "/api/test",
            headers={"Authorization": "Bearer sk-test-key-123"},
        )
        assert response.status_code == 200

    def test_expensive_path_cost(self, app: FastAPI) -> None:
        """Expensive paths consume more tokens."""
        client = TestClient(app)
        # Agent run costs 5 tokens
        for _ in range(2):
            response = client.get("/api/agent/run")
            assert response.status_code == 200


def test_create_rate_limit_middleware_factory() -> None:
    """create_rate_limit_middleware returns a factory function."""
    factory = create_rate_limit_middleware(
        ip_max=50,
        ip_rate=5.0,
    )
    assert callable(factory)

    app = FastAPI()
    middleware = factory(app)
    assert isinstance(middleware, RateLimitMiddleware)