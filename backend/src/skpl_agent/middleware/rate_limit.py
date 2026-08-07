"""FastAPI rate-limit middleware — Token Bucket algorithm per client.

Provides per-IP and per-API-key rate limiting as ASGI middleware.
Compatible with the TokenBucket service layer for shared quota enforcement.

Architecture:
    ┌─ Request ─► RateLimitMiddleware ─► Next Middleware ─► App
    │                  │
    │           ┌──────┴──────┐
    │           ▼              ▼
    │     IP Bucket      API Key Bucket
    │           │              │
    │           └──────┬──────┘
    │                  ▼
    │           Token consumed?
    │           ├─ Yes → 429 Too Many Requests
    │           └─ No  → Continue
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------


@dataclass
class TokenBucket:
    """Token Bucket algorithm implementation.

    Tokens are refilled at a constant rate (tokens_per_second) up to a
    maximum capacity (max_tokens). Each request consumes tokens equal to
    its cost.
    """

    max_tokens: float
    tokens_per_second: float
    tokens: float = field(init=False)
    last_refill: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        self.tokens = self.max_tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.tokens_per_second
        self.tokens = min(self.max_tokens, self.tokens + refill_amount)
        self.last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume tokens. Returns True if successful."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self.tokens

    @property
    def retry_after_seconds(self) -> float:
        """Estimated seconds until enough tokens are available."""
        self._refill()
        deficit = 1.0 - self.tokens
        if deficit <= 0:
            return 0.0
        if self.tokens_per_second <= 0:
            return 60.0
        return deficit / self.tokens_per_second


# ---------------------------------------------------------------------------
# Rate Limit Config
# ---------------------------------------------------------------------------


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Per-IP limits
    ip_max_tokens: int = 100
    ip_tokens_per_second: float = 10.0

    # Per-API-key limits
    key_max_tokens: int = 500
    key_tokens_per_second: float = 50.0

    # Exempt paths (never rate-limited)
    exempt_paths: list[str] = field(default_factory=lambda: [
        "/health",
        "/metrics",
        "/api/health",
        "/api/status",
    ])

    # Paths with higher token costs (e.g., LLM calls)
    expensive_paths: dict[str, float] = field(default_factory=lambda: {
        "/api/agent/run": 5.0,
        "/api/agent/chat": 3.0,
        "/api/desktop/execute": 10.0,
        "/api/firecrawl/scrape": 3.0,
        "/api/firecrawl/crawl": 8.0,
    })

    # Whether to include rate limit headers in responses
    include_headers: bool = True

    # Max age for idle buckets (seconds) — cleanup threshold
    bucket_idle_ttl: float = 3600.0


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware enforcing rate limits per IP and per API key.

    Uses two tiers of Token Buckets:
    - IP-level: Shared across all requests from the same IP
    - API-key-level: Per-authenticated-key (more generous limits)
    """

    def __init__(
        self,
        app,
        config: RateLimitConfig | None = None,
        *,
        get_client_ip: Callable[[Request], str] | None = None,
        get_api_key: Callable[[Request], str | None] | None = None,
    ) -> None:
        super().__init__(app)
        self._config = config or RateLimitConfig()
        self._get_client_ip = get_client_ip or self._default_get_client_ip
        self._get_api_key = get_api_key or self._default_get_api_key
        self._ip_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                max_tokens=self._config.ip_max_tokens,
                tokens_per_second=self._config.ip_tokens_per_second,
            )
        )
        self._key_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                max_tokens=self._config.key_max_tokens,
                tokens_per_second=self._config.key_tokens_per_second,
            )
        )
        self._last_cleanup: float = time.monotonic()

    # ---- ASGI dispatch ----

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Possibly clean up stale buckets
        self._maybe_cleanup()

        # Determine token cost
        token_cost = self._get_token_cost(request.url.path)

        # Check API key bucket first (more generous)
        api_key = self._get_api_key(request)
        if api_key:
            if not self._key_buckets[api_key].consume(token_cost):
                return self._ratelimit_response(
                    self._key_buckets[api_key],
                    tier="api_key",
                )

        # Check IP bucket
        client_ip = self._get_client_ip(request)
        if not self._ip_buckets[client_ip].consume(token_cost):
            return self._ratelimit_response(
                self._ip_buckets[client_ip],
                tier="ip",
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers
        if self._config.include_headers:
            ip_bucket = self._ip_buckets[client_ip]
            response.headers["X-RateLimit-Limit"] = str(self._config.ip_max_tokens)
            response.headers["X-RateLimit-Remaining"] = str(int(ip_bucket.available_tokens))
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + ip_bucket.retry_after_seconds))

        return response

    # ---- Helpers ----

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(exempt) for exempt in self._config.exempt_paths)

    def _get_token_cost(self, path: str) -> float:
        for expensive, cost in self._config.expensive_paths.items():
            if path.startswith(expensive):
                return cost
        return 1.0

    def _ratelimit_response(self, bucket: TokenBucket, tier: str) -> JSONResponse:
        retry_after = int(bucket.retry_after_seconds) + 1
        logger.warning(
            "Rate limit exceeded [tier=%s, retry_after=%ds]", tier, retry_after,
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                "tier": tier,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Tier": tier,
            },
        )

    def _maybe_cleanup(self) -> None:
        """Periodic cleanup of stale buckets to prevent memory leaks."""
        now = time.monotonic()
        if now - self._last_cleanup < 300:  # Every 5 minutes
            return
        self._last_cleanup = now

        ttl = self._config.bucket_idle_ttl
        for buckets in (self._ip_buckets, self._key_buckets):
            stale = [
                key for key, bucket in buckets.items()
                if bucket.available_tokens >= bucket.max_tokens * 0.99
            ]
            for key in stale:
                del buckets[key]

    # ---- Default extractors ----

    @staticmethod
    def _default_get_client_ip(request: Request) -> str:
        """Extract client IP from request headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _default_get_api_key(request: Request) -> str | None:
        """Extract API key from Authorization header."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return request.headers.get("X-API-Key")


# ---------------------------------------------------------------------------
# Convenience Factory
# ---------------------------------------------------------------------------


def create_rate_limit_middleware(
    ip_max: int = 100,
    ip_rate: float = 10.0,
    key_max: int = 500,
    key_rate: float = 50.0,
) -> RateLimitMiddleware:
    """Create a RateLimitMiddleware with custom limits.

    Args:
        ip_max: Maximum tokens per IP bucket.
        ip_rate: Token refill rate per second for IP buckets.
        key_max: Maximum tokens per API key bucket.
        key_rate: Token refill rate per second for API key buckets.

    Returns:
        Configured RateLimitMiddleware (must be added to the FastAPI app).
    """
    config = RateLimitConfig(
        ip_max_tokens=ip_max,
        ip_tokens_per_second=ip_rate,
        key_max_tokens=key_max,
        key_tokens_per_second=key_rate,
    )
    # Return a factory function — the actual middleware needs the app
    return lambda app: RateLimitMiddleware(app, config=config)


__all__ = [
    "RateLimitMiddleware",
    "RateLimitConfig",
    "TokenBucket",
    "create_rate_limit_middleware",
]