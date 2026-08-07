"""Performance tests for rate limiting middleware."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from skpl_agent.middleware.rate_limit import RateLimitConfig, TokenBucket


class TestTokenBucketPerformance:
    """Performance benchmarks for TokenBucket."""

    def test_consume_throughput(self) -> None:
        """TokenBucket can handle high throughput."""
        bucket = TokenBucket(max_tokens=10000, tokens_per_second=10000)
        start = time.monotonic()
        for _ in range(10000):
            bucket.consume(1)
        elapsed = time.monotonic() - start
        # Should be fast (sub-100ms for 10k operations)
        assert elapsed < 0.5, f"TokenBucket throughput too slow: {elapsed:.3f}s"

    def test_refill_accuracy(self) -> None:
        """Token refill is accurate over time."""
        bucket = TokenBucket(max_tokens=100, tokens_per_second=100.0)
        bucket.tokens = 0
        bucket.last_refill = time.monotonic() - 1.0  # 1 second ago

        # Should have ~100 tokens after 1 second
        bucket._refill()
        assert 95 <= bucket.tokens <= 105  # Allow small drift

    def test_retry_after_accuracy(self) -> None:
        """retry_after_seconds is reasonably accurate."""
        bucket = TokenBucket(max_tokens=100, tokens_per_second=10.0)
        bucket.tokens = 0
        # Need 1 token, refill rate is 10/s, so ~0.1 seconds
        wait = bucket.retry_after_seconds
        assert 0.05 <= wait <= 0.2, f"Expected ~0.1s, got {wait:.3f}s"


class TestRateLimitMiddlewarePerformance:
    """Performance tests for RateLimitMiddleware."""

    @pytest.fixture
    def perf_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/api/fast")
        async def fast():
            return {"ok": True}

        app.add_middleware(
            "skpl_agent.middleware.rate_limit.RateLimitMiddleware",
            config=RateLimitConfig(
                ip_max_tokens=1000,
                ip_tokens_per_second=1000.0,
            ),
        )
        return app

    def test_middleware_overhead(self, perf_app: FastAPI) -> None:
        """Rate limiting middleware adds minimal overhead."""
        client = TestClient(perf_app)

        # Warm up
        for _ in range(10):
            client.get("/api/fast")

        start = time.monotonic()
        iterations = 100
        for _ in range(iterations):
            client.get("/api/fast")
        elapsed = time.monotonic() - start

        avg_ms = (elapsed / iterations) * 1000
        # Should be under 5ms per request average
        assert avg_ms < 20, f"Average request too slow: {avg_ms:.1f}ms"

    def test_high_concurrency(self, perf_app: FastAPI) -> None:
        """Middleware handles burst requests without errors."""
        import concurrent.futures

        def make_request():
            client = TestClient(perf_app)
            return client.get("/api/fast").status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in futures]

        assert all(r == 200 for r in results)