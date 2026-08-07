"""Unit tests for firecrawl_service.py — Firecrawl web crawling service.

Tests cover:
- FirecrawlService initialization and configuration
- Crawl lifecycle: start_crawl, get_crawl_status, update_crawl_result,
  list_crawls, cancel_crawl
- Statistics and configuration management
- Error paths: concurrency limits, missing crawls, invalid config
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skpl_agent.app._service.firecrawl_service import (
    CrawlRequest,
    CrawlResult,
    FirecrawlConfig,
    FirecrawlService,
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def default_config() -> FirecrawlConfig:
    """Create a default FirecrawlConfig."""
    return FirecrawlConfig()


@pytest.fixture
def custom_config() -> FirecrawlConfig:
    """Create a custom FirecrawlConfig."""
    return FirecrawlConfig(
        api_key="test-key",
        api_endpoint="https://custom.api.com",
        max_concurrent_crawls=5,
        rate_limit_per_minute=20,
        default_max_pages=100,
        timeout_seconds=600,
        respect_robots_txt=False,
        user_agent="CustomAgent/2.0",
    )


@pytest.fixture
def service(default_config: FirecrawlConfig) -> FirecrawlService:
    """Create a FirecrawlService with default config."""
    return FirecrawlService(config=default_config)


@pytest.fixture
def crawl_request() -> CrawlRequest:
    """Create a sample CrawlRequest."""
    return CrawlRequest(
        url="https://example.com",
        mode="crawl",
        max_pages=10,
        include_patterns=["/docs/*"],
        exclude_patterns=["/admin/*"],
        wait_for=1000,
    )


# ── Configuration Tests ────────────────────────────────────────────────────


class TestFirecrawlConfig:
    """Tests for FirecrawlConfig dataclass."""

    def test_default_values(self) -> None:
        """FirecrawlConfig has sensible defaults."""
        cfg = FirecrawlConfig()
        assert cfg.api_key == ""
        assert cfg.api_endpoint == "https://api.firecrawl.dev"
        assert cfg.max_concurrent_crawls == 3
        assert cfg.rate_limit_per_minute == 10
        assert cfg.default_max_pages == 50
        assert cfg.timeout_seconds == 300
        assert cfg.respect_robots_txt is True
        assert cfg.user_agent == "SKPL-Agent-Firecrawl/0.1"

    def test_custom_values(self, custom_config: FirecrawlConfig) -> None:
        """FirecrawlConfig accepts custom values."""
        assert custom_config.api_key == "test-key"
        assert custom_config.api_endpoint == "https://custom.api.com"
        assert custom_config.max_concurrent_crawls == 5
        assert custom_config.timeout_seconds == 600


class TestFirecrawlServiceInit:
    """Tests for FirecrawlService initialization."""

    def test_init_with_default_config(self) -> None:
        """Service can be initialized without explicit config."""
        svc = FirecrawlService()
        assert svc.config is not None
        assert isinstance(svc.config, FirecrawlConfig)

    def test_init_with_custom_config(self, custom_config: FirecrawlConfig) -> None:
        """Service accepts custom config."""
        svc = FirecrawlService(config=custom_config)
        assert svc.config.api_key == "test-key"
        assert svc.config.max_concurrent_crawls == 5

    def test_config_property(self, service: FirecrawlService) -> None:
        """config property returns the config."""
        assert service.config is not None
        assert isinstance(service.config, FirecrawlConfig)


# ── Update Config Tests ────────────────────────────────────────────────────


class TestUpdateConfig:
    """Tests for update_config method."""

    @pytest.mark.asyncio
    async def test_update_valid_keys(self, service: FirecrawlService) -> None:
        """update_config updates valid configuration keys."""
        cfg = await service.update_config(
            api_key="new-key",
            max_concurrent_crawls=10,
            rate_limit_per_minute=50,
        )
        assert cfg.api_key == "new-key"
        assert cfg.max_concurrent_crawls == 10
        assert cfg.rate_limit_per_minute == 50

    @pytest.mark.asyncio
    async def test_update_ignores_invalid_keys(self, service: FirecrawlService) -> None:
        """update_config silently ignores invalid keys."""
        original = service.config.max_concurrent_crawls
        cfg = await service.update_config(
            invalid_key="should_not_work",
            another_fake="also_ignored",
        )
        assert cfg.max_concurrent_crawls == original
        assert not hasattr(cfg, "invalid_key")

    @pytest.mark.asyncio
    async def test_update_partial(self, service: FirecrawlService) -> None:
        """update_config with partial kwargs only updates specified keys."""
        original_timeout = service.config.timeout_seconds
        cfg = await service.update_config(api_key="partial-update")
        assert cfg.api_key == "partial-update"
        assert cfg.timeout_seconds == original_timeout


# ── Start Crawl Tests ──────────────────────────────────────────────────────


class TestStartCrawl:
    """Tests for start_crawl method."""

    @pytest.mark.asyncio
    async def test_start_crawl_returns_result(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """start_crawl returns a CrawlResult with pending status."""
        result = await service.start_crawl(crawl_request)
        assert isinstance(result, CrawlResult)
        assert result.status == "pending"
        assert result.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_start_crawl_generates_unique_id(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """Each crawl gets a unique ID."""
        r1 = await service.start_crawl(crawl_request)
        r2 = await service.start_crawl(crawl_request)
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_start_crawl_increments_active_count(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """Active crawl count increments after starting."""
        await service.start_crawl(crawl_request)
        stats = await service.get_stats()
        assert stats["active_crawls"] == 1

    @pytest.mark.asyncio
    async def test_start_crawl_respects_concurrency_limit(
        self, custom_config: FirecrawlConfig
    ) -> None:
        """start_crawl raises RuntimeError when concurrency limit reached."""
        svc = FirecrawlService(config=custom_config)  # max_concurrent_crawls=5
        req = CrawlRequest(url="https://example.com")
        for _ in range(5):
            await svc.start_crawl(req)
        with pytest.raises(RuntimeError, match="Max concurrent crawls"):
            await svc.start_crawl(req)

    @pytest.mark.asyncio
    async def test_start_crawl_with_scrape_mode(
        self, service: FirecrawlService
    ) -> None:
        """start_crawl works with scrape mode."""
        req = CrawlRequest(url="https://example.com", mode="scrape")
        result = await service.start_crawl(req)
        assert result.status == "pending"


# ── Get Crawl Status Tests ─────────────────────────────────────────────────


class TestGetCrawlStatus:
    """Tests for get_crawl_status method."""

    @pytest.mark.asyncio
    async def test_get_existing_crawl(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """get_crawl_status returns the crawl for a valid ID."""
        result = await service.start_crawl(crawl_request)
        status = await service.get_crawl_status(result.id)
        assert status is not None
        assert status.id == result.id
        assert status.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_crawl(self, service: FirecrawlService) -> None:
        """get_crawl_status returns None for unknown ID."""
        status = await service.get_crawl_status("nonexistent-id")
        assert status is None


# ── Update Crawl Result Tests ──────────────────────────────────────────────


class TestUpdateCrawlResult:
    """Tests for update_crawl_result method."""

    @pytest.mark.asyncio
    async def test_update_to_completed(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """update_crawl_result updates status to completed."""
        result = await service.start_crawl(crawl_request)
        updated = await service.update_crawl_result(
            result.id,
            status="completed",
            pages_crawled=5,
            pages_failed=0,
            content=[{"url": "https://example.com/page1", "title": "Page 1"}],
        )
        assert updated is not None
        assert updated.status == "completed"
        assert updated.pages_crawled == 5
        assert len(updated.content) == 1
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_to_failed(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """update_crawl_result updates status to failed with error."""
        result = await service.start_crawl(crawl_request)
        updated = await service.update_crawl_result(
            result.id,
            status="failed",
            error="DNS resolution failed",
        )
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error == "DNS resolution failed"
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_nonexistent_crawl(self, service: FirecrawlService) -> None:
        """update_crawl_result returns None for unknown ID."""
        updated = await service.update_crawl_result("nonexistent", status="completed")
        assert updated is None

    @pytest.mark.asyncio
    async def test_update_decrements_active_on_completion(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """Active crawl count decrements when crawl completes."""
        result = await service.start_crawl(crawl_request)
        stats_before = await service.get_stats()
        assert stats_before["active_crawls"] == 1
        await service.update_crawl_result(result.id, status="completed")
        stats_after = await service.get_stats()
        assert stats_after["active_crawls"] == 0


# ── List Crawls Tests ──────────────────────────────────────────────────────


class TestListCrawls:
    """Tests for list_crawls method."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service: FirecrawlService) -> None:
        """list_crawls returns empty list when no crawls exist."""
        crawls = await service.list_crawls()
        assert crawls == []

    @pytest.mark.asyncio
    async def test_list_returns_all(self, service: FirecrawlService) -> None:
        """list_crawls returns all crawls."""
        for i in range(3):
            req = CrawlRequest(url=f"https://example{i}.com")
            await service.start_crawl(req)
        crawls = await service.list_crawls()
        assert len(crawls) == 3

    @pytest.mark.asyncio
    async def test_list_respects_limit(self, service: FirecrawlService) -> None:
        """list_crawls respects the limit parameter."""
        for i in range(10):
            req = CrawlRequest(url=f"https://example{i}.com")
            await service.start_crawl(req)
        crawls = await service.list_crawls(limit=3)
        assert len(crawls) == 3

    @pytest.mark.asyncio
    async def test_list_sorted_by_created_at_desc(
        self, service: FirecrawlService
    ) -> None:
        """list_crawls returns results sorted by created_at descending."""
        req1 = CrawlRequest(url="https://first.com")
        r1 = await service.start_crawl(req1)
        req2 = CrawlRequest(url="https://second.com")
        r2 = await service.start_crawl(req2)
        crawls = await service.list_crawls()
        # Most recent first
        assert crawls[0].id == r2.id
        assert crawls[1].id == r1.id


# ── Cancel Crawl Tests ─────────────────────────────────────────────────────


class TestCancelCrawl:
    """Tests for cancel_crawl method."""

    @pytest.mark.asyncio
    async def test_cancel_active_crawl(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """cancel_crawl cancels an active crawl."""
        result = await service.start_crawl(crawl_request)
        success = await service.cancel_crawl(result.id)
        assert success is True
        # Verify status changed
        status = await service.get_crawl_status(result.id)
        assert status.status == "failed"
        assert status.error == "Cancelled by user"

    @pytest.mark.asyncio
    async def test_cancel_completed_crawl(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """cancel_crawl returns False for completed crawls."""
        result = await service.start_crawl(crawl_request)
        await service.update_crawl_result(result.id, status="completed")
        success = await service.cancel_crawl(result.id)
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_crawl(self, service: FirecrawlService) -> None:
        """cancel_crawl returns False for unknown IDs."""
        success = await service.cancel_crawl("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_decrements_active_count(
        self, service: FirecrawlService, crawl_request: CrawlRequest
    ) -> None:
        """Active count decrements after cancellation."""
        result = await service.start_crawl(crawl_request)
        await service.cancel_crawl(result.id)
        stats = await service.get_stats()
        assert stats["active_crawls"] == 0


# ── Get Stats Tests ────────────────────────────────────────────────────────


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.asyncio
    async def test_stats_empty(self, service: FirecrawlService) -> None:
        """get_stats returns zeros for empty service."""
        stats = await service.get_stats()
        assert stats["total_crawls"] == 0
        assert stats["completed_crawls"] == 0
        assert stats["failed_crawls"] == 0
        assert stats["active_crawls"] == 0
        assert stats["total_pages_crawled"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_mixed_statuses(
        self, service: FirecrawlService
    ) -> None:
        """get_stats correctly counts crawls by status."""
        # Completed
        r1 = await service.start_crawl(CrawlRequest(url="https://a.com"))
        await service.update_crawl_result(r1.id, status="completed", pages_crawled=10)
        # Failed
        r2 = await service.start_crawl(CrawlRequest(url="https://b.com"))
        await service.update_crawl_result(r2.id, status="failed", pages_crawled=2)
        # Pending
        await service.start_crawl(CrawlRequest(url="https://c.com"))

        stats = await service.get_stats()
        assert stats["total_crawls"] == 3
        assert stats["completed_crawls"] == 1
        assert stats["failed_crawls"] == 1
        assert stats["active_crawls"] == 1
        assert stats["total_pages_crawled"] == 12

    @pytest.mark.asyncio
    async def test_stats_keys_present(self, service: FirecrawlService) -> None:
        """get_stats returns all expected keys."""
        stats = await service.get_stats()
        expected_keys = {
            "total_crawls", "completed_crawls", "failed_crawls",
            "active_crawls", "total_pages_crawled",
        }
        assert set(stats.keys()) == expected_keys


# ── CrawlRequest Tests ─────────────────────────────────────────────────────


class TestCrawlRequest:
    """Tests for CrawlRequest dataclass."""

    def test_default_values(self) -> None:
        """CrawlRequest has sensible defaults."""
        req = CrawlRequest(url="https://example.com")
        assert req.url == "https://example.com"
        assert req.mode == "crawl"
        assert req.max_pages == 10
        assert req.include_patterns == []
        assert req.exclude_patterns == []
        assert req.wait_for == 0

    def test_custom_values(self) -> None:
        """CrawlRequest accepts custom values."""
        req = CrawlRequest(
            url="https://example.com",
            mode="scrape",
            max_pages=1,
            include_patterns=["/blog/*"],
            exclude_patterns=["/private/*"],
            wait_for=2000,
        )
        assert req.mode == "scrape"
        assert req.max_pages == 1
        assert req.include_patterns == ["/blog/*"]
        assert req.exclude_patterns == ["/private/*"]
        assert req.wait_for == 2000


# ── CrawlResult Tests ──────────────────────────────────────────────────────


class TestCrawlResult:
    """Tests for CrawlResult dataclass."""

    def test_default_values(self) -> None:
        """CrawlResult has sensible defaults."""
        result = CrawlResult()
        assert result.id != ""
        assert len(result.id) == 32  # uuid4 hex
        assert result.status == "pending"
        assert result.pages_crawled == 0
        assert result.pages_failed == 0
        assert result.content == []
        assert result.error is None
        assert result.completed_at is None

    def test_created_at_is_set(self) -> None:
        """created_at is automatically set."""
        result = CrawlResult()
        assert result.created_at is not None

    def test_custom_values(self) -> None:
        """CrawlResult accepts custom values."""
        result = CrawlResult(
            url="https://example.com",
            status="completed",
            pages_crawled=42,
            pages_failed=3,
            content=[{"url": "https://example.com/page1"}],
            error=None,
        )
        assert result.url == "https://example.com"
        assert result.status == "completed"
        assert result.pages_crawled == 42
        assert result.pages_failed == 3
        assert len(result.content) == 1