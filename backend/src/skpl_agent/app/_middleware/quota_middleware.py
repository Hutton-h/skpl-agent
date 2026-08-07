"""Quota enforcement middleware.

Checks and enforces per-tenant resource quotas on incoming requests.
Raises HTTP 429 (Too Many Requests) or 403 (Forbidden) when quotas are exceeded.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class QuotaMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces per-tenant rate limits and quotas.

    Uses a token bucket algorithm for rate limiting and delegates
    resource-specific checks to the QuotaService.
    """

    def __init__(
        self,
        app: Any,
        quota_service: Any = None,
        default_rate_limit: int = 100,
        default_window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self._quota_service = quota_service
        self._default_rate_limit = default_rate_limit
        self._default_window_seconds = default_window_seconds
        # Initialize token bucket with full tokens to avoid 429 on first request
        self._buckets: dict[str, tuple[float, int]] = defaultdict(
            lambda: (time.time(), self._default_rate_limit)
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Check quotas before processing the request."""
        # Skip quota checks for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Extract tenant from header or use default
        tenant_id = request.headers.get("X-Tenant-ID", "default")

        # Rate limit check (token bucket)
        if not self._check_rate_limit(tenant_id):
            logger.warning("Rate limit exceeded for tenant: %s", tenant_id)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "tenant_id": tenant_id,
                },
            )

        # If quota service is available, do resource-specific checks
        if self._quota_service:
            # Check API request quota
            result = await self._quota_service.check_quota(
                tenant_id, "api_requests"
            )
            if not result.allowed:
                logger.warning(
                    "API quota exceeded for tenant %s: %s",
                    tenant_id,
                    result.message,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": result.message,
                        "tenant_id": tenant_id,
                        "resource": result.resource,
                        "current": result.current,
                        "limit": result.limit,
                    },
                )

            # Increment usage
            await self._quota_service.increment_usage(
                tenant_id, api_requests=1
            )

        # Process the request
        response = await call_next(request)

        # Track token usage from response headers if available
        if self._quota_service:
            tokens_header = response.headers.get("X-Tokens-Used")
            if tokens_header:
                try:
                    tokens = int(tokens_header)
                    await self._quota_service.increment_usage(
                        tenant_id, tokens=tokens
                    )
                except (ValueError, TypeError):
                    pass

        return response

    def _check_rate_limit(self, tenant_id: str) -> bool:
        """Token bucket rate limit check."""
        now = time.time()
        last_time, tokens = self._buckets[tenant_id]

        # Refill tokens based on elapsed time
        elapsed = now - last_time
        refill_rate = self._default_rate_limit / self._default_window_seconds
        new_tokens = int(elapsed * refill_rate)
        tokens = min(self._default_rate_limit, tokens + new_tokens)
        last_time = now

        if tokens > 0:
            tokens -= 1
            self._buckets[tenant_id] = (last_time, tokens)
            return True

        self._buckets[tenant_id] = (last_time, tokens)
        return False
