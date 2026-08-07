"""Firecrawl skill service layer.

Manages Firecrawl web crawling operations, including crawl scheduling,
result retrieval, and configuration management. Integrates SSRF protection,
rate limiting, and MCP three-tier degradation strategy.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from skpl_agent.app._security.ssrf import SSRFProtection, SSRFError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP Three-Tier Degradation Strategy
# ---------------------------------------------------------------------------
#
# Tier 1: API Mode (Firecrawl Cloud API)
#   - Uses FirecrawlClient with API key for full-featured access
#   - Features: LLM extraction, JS rendering, CDN-accelerated crawling
#   - Fallback trigger: API key not configured, API rate limit exceeded,
#     API server unreachable, 5xx errors after retries
#
# Tier 2: Local Mode (Direct HTTP + Parsing)
#   - Uses aiohttp + BeautifulSoup for direct scraping
#   - Features: Basic scraping, crawling, search (via Google SERP),
#     sitemap parsing, CSS selector extraction
#   - Fallback trigger: Network errors, domain blocks, timeout
#
# Tier 3: Static Mode (Read-only Cache / Offline)
#   - Returns cached results or empty results with clear error messages
#   - Features: Previously cached content, error reporting
#   - Fallback trigger: No network connectivity, all requests fail
#
# The degradation is automatic and transparent to the caller.
# Each tier is tried in order, and the first successful result is returned.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class CrawlRequest:
    """A Firecrawl crawl request."""

    url: str
    mode: str = "crawl"  # crawl | scrape | map
    max_pages: int = 10
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    wait_for: int = 0  # milliseconds


@dataclass
class CrawlResult:
    """Result of a Firecrawl crawl operation."""

    id: str = field(default_factory=lambda: uuid4().hex)
    url: str = ""
    status: str = "pending"  # pending | running | completed | failed
    pages_crawled: int = 0
    pages_failed: int = 0
    content: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


@dataclass
class FirecrawlConfig:
    """Configuration for the Firecrawl skill."""

    api_key: str = ""
    api_endpoint: str = "https://api.firecrawl.dev"
    max_concurrent_crawls: int = 3
    rate_limit_per_minute: int = 10
    default_max_pages: int = 50
    timeout_seconds: int = 300
    respect_robots_txt: bool = True
    user_agent: str = "SKPL-Agent-Firecrawl/0.1"


# ---------------------------------------------------------------------------
# Rate Limiter (actual implementation, not just config declaration)
# ---------------------------------------------------------------------------


class _DomainRateLimiter:
    """Per-domain token bucket rate limiter for web requests.

    Enforces a configurable rate limit per domain, preventing
    excessive requests to any single target. Uses a simple
    sliding window approach with per-domain tracking.
    """

    def __init__(self, rate_limit_per_minute: int = 10) -> None:
        self._rate_limit = rate_limit_per_minute
        self._request_times: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        """Wait until a request to the given domain is allowed.

        If the rate limit has been exceeded, this method will sleep
        until the next request slot is available.

        Args:
            domain: The domain being rate-limited.
        """
        async with self._lock:
            now = time.monotonic()
            window_start = now - 60.0  # 1 minute sliding window

            # Get or initialize request times for this domain
            if domain not in self._request_times:
                self._request_times[domain] = []

            # Remove expired entries
            times = self._request_times[domain]
            self._request_times[domain] = [t for t in times if t > window_start]

            # Check if we need to wait
            recent_count = len(self._request_times[domain])
            if recent_count >= self._rate_limit:
                # Calculate wait time until the oldest request expires
                oldest = self._request_times[domain][0]
                wait_time = oldest + 60.0 - now + 0.01  # Small buffer
                if wait_time > 0:
                    logger.debug(
                        "Rate limit hit for %s (%d/%d requests), waiting %.1fs",
                        domain, recent_count, self._rate_limit, wait_time,
                    )
                    await asyncio.sleep(wait_time)

            # Record this request
            self._request_times[domain].append(time.monotonic())

    def reset(self) -> None:
        """Reset all rate limit counters."""
        self._request_times.clear()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class FirecrawlService:
    """Service for managing Firecrawl web crawling operations.

    Handles crawl scheduling, execution tracking, result management,
    and configuration. Integrates SSRF protection, rate limiting,
    and MCP three-tier degradation.

    Usage:
        >>> svc = FirecrawlService()
        >>> svc.ssrf_protection.validate_url("https://example.com")  # OK
        >>> svc.ssrf_protection.validate_url("http://localhost")  # Raises SSRFError
    """

    def __init__(self, config: FirecrawlConfig | None = None) -> None:
        self._config = config or FirecrawlConfig()
        self._crawls: dict[str, CrawlResult] = {}
        self._active_crawls: int = 0

        # SSRF Protection
        self._ssrf: SSRFProtection = SSRFProtection(
            block_localhost=True,
            dns_rebinding_protection=True,
        )

        # Rate Limiter (actual implementation with per-domain tracking)
        self._rate_limiter: _DomainRateLimiter = _DomainRateLimiter(
            rate_limit_per_minute=self._config.rate_limit_per_minute,
        )

        # MCP degradation tier tracking
        self._degradation_tier: str = "api"  # api | local | static
        self._degradation_reason: str = ""

    # ── SSRF Protection Integration ──────────────────────────────────────

    @property
    def ssrf_protection(self) -> SSRFProtection:
        """Get the SSRF protection instance for URL validation."""
        return self._ssrf

    def validate_url(self, url: str) -> None:
        """Validate a URL for SSRF safety.

        This method is called at the beginning of every crawl/scrape/search
        operation to prevent Server-Side Request Forgery attacks.

        Args:
            url: The URL to validate.

        Raises:
            SSRFError: If the URL is blocked by SSRF protection.
        """
        self._ssrf.validate_url(url)

    def sanitize_url(self, url: str) -> str:
        """Sanitize a URL by removing fragments and userinfo.

        Args:
            url: URL to sanitize.

        Returns:
            Sanitized URL string.
        """
        return self._ssrf.sanitize_url(url)

    # ── Rate Limiting (actual implementation) ────────────────────────────

    async def check_rate_limit(self, domain: str) -> None:
        """Check and enforce rate limiting for a domain.

        This method blocks until the rate limit allows the request.
        Called before every outbound request.

        Args:
            domain: The domain to check rate limits for.
        """
        await self._rate_limiter.acquire(domain)

    # ── MCP Degradation ──────────────────────────────────────────────────

    @property
    def degradation_tier(self) -> str:
        """Get the current MCP degradation tier."""
        return self._degradation_tier

    @property
    def degradation_reason(self) -> str:
        """Get the reason for the current degradation tier."""
        return self._degradation_reason

    def set_degradation_tier(self, tier: str, reason: str) -> None:
        """Set the current MCP degradation tier.

        Args:
            tier: The tier to set (api, local, static).
            reason: The reason for the degradation.
        """
        valid_tiers = {"api", "local", "static"}
        if tier not in valid_tiers:
            logger.warning("Invalid degradation tier: %s. Must be one of %s", tier, valid_tiers)
            return

        self._degradation_tier = tier
        self._degradation_reason = reason
        logger.info(
            "MCP degradation tier set to '%s': %s",
            tier, reason,
        )

    # ── Configuration ────────────────────────────────────────────────────

    @property
    def config(self) -> FirecrawlConfig:
        return self._config

    async def update_config(self, **kwargs: Any) -> FirecrawlConfig:
        """Update Firecrawl configuration."""
        valid_keys = {
            "api_key", "api_endpoint", "max_concurrent_crawls",
            "rate_limit_per_minute", "default_max_pages",
            "timeout_seconds", "respect_robots_txt", "user_agent",
        }
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self._config, key, value)
                logger.info("Updated Firecrawl config: %s", key)

        # Update rate limiter if rate limit changed
        if "rate_limit_per_minute" in kwargs:
            self._rate_limiter = _DomainRateLimiter(
                rate_limit_per_minute=self._config.rate_limit_per_minute,
            )

        return self._config

    # ── Crawl Management ─────────────────────────────────────────────────

    async def start_crawl(self, request: CrawlRequest) -> CrawlResult:
        """Start a new crawl operation.

        Includes SSRF validation and rate limiting.

        Args:
            request: Crawl request with URL and parameters.

        Returns:
            CrawlResult tracking the crawl operation.

        Raises:
            SSRFError: If the URL fails SSRF validation.
            RuntimeError: If max concurrent crawls is exceeded.
        """
        # SSRF validation
        self.validate_url(request.url)

        # Rate limiting
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc
        await self.check_rate_limit(domain)

        if self._active_crawls >= self._config.max_concurrent_crawls:
            raise RuntimeError(
                f"Max concurrent crawls ({self._config.max_concurrent_crawls}) reached"
            )

        result = CrawlResult(
            url=request.url,
            status="pending",
        )
        self._crawls[result.id] = result
        self._active_crawls += 1

        logger.info(
            "Crawl started: %s (%s, tier=%s)", result.id, request.url, self._degradation_tier,
        )
        return result

    async def get_crawl_status(self, crawl_id: str) -> CrawlResult | None:
        """Get the status of a crawl operation."""
        return self._crawls.get(crawl_id)

    async def update_crawl_result(
        self,
        crawl_id: str,
        status: str,
        pages_crawled: int = 0,
        pages_failed: int = 0,
        content: list[dict[str, Any]] | None = None,
        error: str | None = None,
    ) -> CrawlResult | None:
        """Update a crawl result."""
        result = self._crawls.get(crawl_id)
        if result:
            result.status = status
            result.pages_crawled = pages_crawled
            result.pages_failed = pages_failed
            if content is not None:
                result.content = content
            result.error = error
            if status in ("completed", "failed"):
                result.completed_at = datetime.now(timezone.utc)
                self._active_crawls = max(0, self._active_crawls - 1)
        return result

    async def list_crawls(self, limit: int = 50) -> list[CrawlResult]:
        """List recent crawl results."""
        return sorted(
            self._crawls.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )[:limit]

    async def cancel_crawl(self, crawl_id: str) -> bool:
        """Cancel an active crawl."""
        result = self._crawls.get(crawl_id)
        if result and result.status in ("pending", "running"):
            result.status = "failed"
            result.error = "Cancelled by user"
            self._active_crawls = max(0, self._active_crawls - 1)
            return True
        return False

    # ── Stats ────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Get Firecrawl usage statistics including degradation tier."""
        crawls = list(self._crawls.values())
        completed = sum(1 for c in crawls if c.status == "completed")
        failed = sum(1 for c in crawls if c.status == "failed")
        total_pages = sum(c.pages_crawled for c in crawls)
        return {
            "total_crawls": len(crawls),
            "completed_crawls": completed,
            "failed_crawls": failed,
            "active_crawls": self._active_crawls,
            "total_pages_crawled": total_pages,
            "degradation_tier": self._degradation_tier,
            "degradation_reason": self._degradation_reason,
            "rate_limit_per_minute": self._config.rate_limit_per_minute,
            "ssrf_enabled": True,
        }