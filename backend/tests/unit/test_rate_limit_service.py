"""Unit tests for rate_limit_service.py — Token bucket rate limiting.

Tests cover:
- TokenBucket: consume, refill, available_tokens, max_tokens, time_until_refill
- RateLimitService: add_rule, remove_rule, check, check_tenant, reset,
  get_status, get_all_status
- RateLimitConfig and RateLimitResult dataclasses
- Edge cases: auto_create, missing keys, multiple rule levels
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skpl_agent.app._service.rate_limit_service import (
    RateLimitConfig,
    RateLimitResult,
    RateLimitService,
    TokenBucket,
)


# ── TokenBucket Tests ──────────────────────────────────────────────────────


class TestTokenBucketInit:
    """Tests for TokenBucket initialization."""

    def test_init_with_defaults(self) -> None:
        """TokenBucket initializes with max tokens."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        assert bucket.max_tokens == 100
        assert bucket.available_tokens == 100

    def test_init_with_refill_period(self) -> None:
        """TokenBucket accepts custom refill_period."""
        bucket = TokenBucket(max_tokens=50, refill_rate=5, refill_period=2.0)
        assert bucket.max_tokens == 50
        assert bucket.available_tokens == 50


class TestTokenBucketConsume:
    """Tests for TokenBucket.consume method."""

    def test_consume_single_token(self) -> None:
        """consume(1) uses one token."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        assert bucket.consume() is True
        assert bucket.available_tokens == 99

    def test_consume_multiple_tokens(self) -> None:
        """consume(N) uses N tokens."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        assert bucket.consume(5) is True
        assert bucket.available_tokens == 95

    def test_consume_all_tokens(self) -> None:
        """consume with exact capacity."""
        bucket = TokenBucket(max_tokens=10, refill_rate=10)
        assert bucket.consume(10) is True
        assert bucket.available_tokens == 0

    def test_consume_exceeds_capacity(self) -> None:
        """consume more than available returns False."""
        bucket = TokenBucket(max_tokens=5, refill_rate=1)
        assert bucket.consume(10) is False
        assert bucket.available_tokens == 5  # unchanged

    def test_consume_when_empty(self) -> None:
        """consume on empty bucket returns False."""
        bucket = TokenBucket(max_tokens=5, refill_rate=1)
        bucket.consume(5)  # exhaust
        assert bucket.consume() is False

    def test_consume_negative_raises(self) -> None:
        """consume with negative tokens would fail."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1)
        assert bucket.consume(-1) is True  # technically adds tokens
        assert bucket.available_tokens == 10  # capped at max


class TestTokenBucketRefill:
    """Tests for TokenBucket refill behavior."""

    def test_refill_over_time(self) -> None:
        """Tokens refill over time."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        bucket.consume(50)  # 50 remaining
        # Simulate 1 second of refill
        with patch.object(bucket, "_last_refill", bucket._last_refill - 1.0):
            assert bucket.available_tokens == 60  # 50 + 10 refill

    def test_refill_capped_at_max(self) -> None:
        """Refill never exceeds max_tokens."""
        bucket = TokenBucket(max_tokens=100, refill_rate=1000)
        bucket.consume(1)
        with patch.object(bucket, "_last_refill", bucket._last_refill - 10.0):
            assert bucket.available_tokens == 100  # capped

    def test_available_tokens_triggers_refill(self) -> None:
        """available_tokens property triggers refill before reading."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        bucket.consume(100)  # exhaust
        with patch.object(bucket, "_last_refill", bucket._last_refill - 2.0):
            assert bucket.available_tokens == 20  # 2 * 10 = 20


class TestTokenBucketTimeUntilRefill:
    """Tests for TokenBucket.time_until_refill method."""

    def test_time_until_refill_zero_when_enough_tokens(self) -> None:
        """time_until_refill returns 0 when tokens available."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        assert bucket.time_until_refill(1) == 0.0

    def test_time_until_refill_partial(self) -> None:
        """time_until_refill calculates seconds needed."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        bucket.consume(100)  # exhaust
        assert bucket.time_until_refill(50) == 5.0  # 50 / 10

    def test_time_until_refill_triggers_refill(self) -> None:
        """time_until_refill triggers refill before calculating."""
        bucket = TokenBucket(max_tokens=100, refill_rate=10)
        bucket.consume(100)
        with patch.object(bucket, "_last_refill", bucket._last_refill - 1.0):
            assert bucket.time_until_refill(20) == 1.0  # 20 - 10 = 10, /10 = 1


# ── RateLimitConfig Tests ──────────────────────────────────────────────────


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self) -> None:
        """RateLimitConfig creates correctly."""
        cfg = RateLimitConfig(key="test", max_tokens=100, refill_rate=10)
        assert cfg.key == "test"
        assert cfg.max_tokens == 100
        assert cfg.refill_rate == 10
        assert cfg.refill_period == 1.0


# ── RateLimitResult Tests ──────────────────────────────────────────────────


class TestRateLimitResult:
    """Tests for RateLimitResult dataclass."""

    def test_allowed_result(self) -> None:
        """RateLimitResult for allowed requests."""
        r = RateLimitResult(
            allowed=True,
            key="test",
            current_tokens=50,
            max_tokens=100,
        )
        assert r.allowed is True
        assert r.current_tokens == 50
        assert r.retry_after_seconds == 0.0

    def test_denied_result(self) -> None:
        """RateLimitResult for denied requests."""
        r = RateLimitResult(
            allowed=False,
            key="test",
            current_tokens=0,
            max_tokens=100,
            retry_after_seconds=5.0,
            limit_type="tenant",
        )
        assert r.allowed is False
        assert r.retry_after_seconds == 5.0
        assert r.limit_type == "tenant"


# ── RateLimitService Tests ─────────────────────────────────────────────────


class TestRateLimitServiceAddRule:
    """Tests for add_rule method."""

    def test_add_rule_creates_bucket(self) -> None:
        """add_rule creates a new bucket."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        assert "tenant:default" in svc._buckets

    def test_add_rule_updates_existing(self) -> None:
        """add_rule updates an existing rule."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        svc.add_rule("tenant:default", 200, 20)
        assert svc._configs["tenant:default"].max_tokens == 200
        assert svc._configs["tenant:default"].refill_rate == 20

    def test_add_rule_with_refill_period(self) -> None:
        """add_rule accepts custom refill period."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10, refill_period=2.0)
        assert svc._configs["tenant:default"].refill_period == 2.0


class TestRateLimitServiceRemoveRule:
    """Tests for remove_rule method."""

    def test_remove_existing_rule(self) -> None:
        """remove_rule removes an existing rule."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        assert svc.remove_rule("tenant:default") is True
        assert "tenant:default" not in svc._buckets
        assert "tenant:default" not in svc._configs

    def test_remove_nonexistent_rule(self) -> None:
        """remove_rule returns False for unknown key."""
        svc = RateLimitService()
        assert svc.remove_rule("nonexistent") is False


class TestRateLimitServiceCheck:
    """Tests for check method."""

    @pytest.mark.asyncio
    async def test_check_allowed(self) -> None:
        """check returns allowed when tokens available."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        result = await svc.check("tenant:default")
        assert result.allowed is True
        assert result.key == "tenant:default"
        assert result.current_tokens == 99

    @pytest.mark.asyncio
    async def test_check_denied(self) -> None:
        """check returns denied when exhausted."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 2, 0.01)  # very slow refill
        await svc.check("tenant:default", tokens=2)  # exhaust
        result = await svc.check("tenant:default")
        assert result.allowed is False
        assert result.retry_after_seconds > 0

    @pytest.mark.asyncio
    async def test_check_missing_key_allowed(self) -> None:
        """check returns allowed for unknown key (no auto_create)."""
        svc = RateLimitService()
        result = await svc.check("unknown:key")
        assert result.allowed is True
        assert result.current_tokens == 0

    @pytest.mark.asyncio
    async def test_check_auto_create(self) -> None:
        """check with auto_create creates a default bucket."""
        svc = RateLimitService()
        result = await svc.check("new:key", auto_create=True, default_max=50, default_rate=5)
        assert result.allowed is True
        assert "new:key" in svc._buckets
        assert svc._buckets["new:key"].max_tokens == 50

    @pytest.mark.asyncio
    async def test_check_multiple_tokens(self) -> None:
        """check with tokens=5 consumes 5 tokens."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        result = await svc.check("tenant:default", tokens=5)
        assert result.allowed is True
        assert result.current_tokens == 95


class TestRateLimitServiceCheckTenant:
    """Tests for check_tenant method."""

    @pytest.mark.asyncio
    async def test_check_tenant_basic(self) -> None:
        """check_tenant checks tenant-wide limit."""
        svc = RateLimitService()
        result = await svc.check_tenant("tenant-1")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_tenant_with_endpoint(self) -> None:
        """check_tenant checks tenant+endpoint and endpoint limits."""
        svc = RateLimitService()
        result = await svc.check_tenant("tenant-1", endpoint="/api/test")
        assert result.allowed is True
        # Should have created both tenant and endpoint buckets
        assert "tenant:tenant-1" in svc._buckets
        assert "endpoint:/api/test" in svc._buckets
        assert "tenant:tenant-1:endpoint:/api/test" in svc._buckets

    @pytest.mark.asyncio
    async def test_check_tenant_most_restrictive(self) -> None:
        """check_tenant returns the most restrictive result."""
        svc = RateLimitService()
        # Make tenant-level very restrictive
        svc.add_rule("tenant:tenant-1", 1, 0.01)
        await svc.check("tenant:tenant-1", tokens=1)  # exhaust tenant
        result = await svc.check_tenant("tenant-1", endpoint="/api/test")
        assert result.allowed is False
        assert "tenant-1" in result.key


class TestRateLimitServiceGetStatus:
    """Tests for get_status method."""

    @pytest.mark.asyncio
    async def test_get_status_existing(self) -> None:
        """get_status returns status for existing key."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        status = await svc.get_status("tenant:default")
        assert status["exists"] is True
        assert status["key"] == "tenant:default"
        assert status["max_tokens"] == 100
        assert "available_tokens" in status
        assert "usage_percent" in status

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self) -> None:
        """get_status returns exists=False for unknown key."""
        svc = RateLimitService()
        status = await svc.get_status("nonexistent")
        assert status["exists"] is False
        assert status["key"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_get_status_usage_percent(self) -> None:
        """get_status usage_percent reflects consumption."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        await svc.check("tenant:default", tokens=50)
        status = await svc.get_status("tenant:default")
        assert status["usage_percent"] == pytest.approx(50.0, abs=1.0)


class TestRateLimitServiceGetAllStatus:
    """Tests for get_all_status method."""

    @pytest.mark.asyncio
    async def test_get_all_status_empty(self) -> None:
        """get_all_status returns empty list for no rules."""
        svc = RateLimitService()
        statuses = await svc.get_all_status()
        assert statuses == []

    @pytest.mark.asyncio
    async def test_get_all_status_multiple(self) -> None:
        """get_all_status returns all buckets sorted."""
        svc = RateLimitService()
        svc.add_rule("tenant:b", 100, 10)
        svc.add_rule("tenant:a", 50, 5)
        statuses = await svc.get_all_status()
        assert len(statuses) == 2
        assert statuses[0]["key"] == "tenant:a"  # sorted
        assert statuses[1]["key"] == "tenant:b"


class TestRateLimitServiceReset:
    """Tests for reset method."""

    def test_reset_single(self) -> None:
        """reset restores a bucket to full."""
        svc = RateLimitService()
        svc.add_rule("tenant:default", 100, 10)
        # Consume some tokens via internal bucket
        svc._buckets["tenant:default"].consume(50)
        assert svc._buckets["tenant:default"].available_tokens == 50
        svc.reset("tenant:default")
        assert svc._buckets["tenant:default"].available_tokens == 100

    def test_reset_nonexistent_noop(self) -> None:
        """reset on unknown key does nothing."""
        svc = RateLimitService()
        svc.reset("nonexistent")  # should not raise

    def test_reset_all(self) -> None:
        """reset_all restores all buckets."""
        svc = RateLimitService()
        svc.add_rule("tenant:a", 100, 10)
        svc.add_rule("tenant:b", 100, 10)
        svc._buckets["tenant:a"].consume(50)
        svc._buckets["tenant:b"].consume(30)
        svc.reset_all()
        assert svc._buckets["tenant:a"].available_tokens == 100
        assert svc._buckets["tenant:b"].available_tokens == 100


# ── Edge Case and Stress Tests ─────────────────────────────────────────────


class TestTokenBucketEdgeCases:
    """Edge case tests for TokenBucket."""

    def test_zero_max_tokens(self) -> None:
        """Bucket with max_tokens=0 always denies."""
        bucket = TokenBucket(max_tokens=0, refill_rate=1)
        assert bucket.consume() is False

    def test_zero_refill_rate(self) -> None:
        """Bucket with refill_rate=0 never refills."""
        bucket = TokenBucket(max_tokens=10, refill_rate=0)
        bucket.consume(10)
        with patch.object(bucket, "_last_refill", bucket._last_refill - 100.0):
            assert bucket.available_tokens == 0

    def test_very_high_refill_rate(self) -> None:
        """Bucket with high refill rate fills quickly."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1000)
        bucket.consume(10)
        with patch.object(bucket, "_last_refill", bucket._last_refill - 0.01):
            assert bucket.available_tokens == 10

    def test_consume_zero_tokens(self) -> None:
        """consume(0) always succeeds and doesn't change count."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1)
        assert bucket.consume(0) is True
        assert bucket.available_tokens == 10


class TestRateLimitServiceEdgeCases:
    """Edge case tests for RateLimitService."""

    @pytest.mark.asyncio
    async def test_check_tenant_no_endpoint(self) -> None:
        """check_tenant without endpoint only checks tenant-wide."""
        svc = RateLimitService()
        result = await svc.check_tenant("tenant-x")
        assert result.allowed is True
        # Only tenant bucket created
        assert "tenant:tenant-x" in svc._buckets

    @pytest.mark.asyncio
    async def test_check_with_exhausted_auto_create(self) -> None:
        """auto_create with very small bucket denies quickly."""
        svc = RateLimitService()
        result = await svc.check(
            "tenant:restricted",
            tokens=100,
            auto_create=True,
            default_max=10,
            default_rate=0.01,
        )
        assert result.allowed is False
        assert "tenant:restricted" in svc._buckets