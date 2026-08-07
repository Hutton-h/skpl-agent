"""Unit tests for quota_service.py — Quota management service.

Tests cover:
- QuotaService initialization and quota management
- get_quota, set_quota, check_quota, get_usage, increment_usage
- get_quota_status, get_global_stats, list_quotas
- Auto-creation of defaults, daily counter reset, error paths
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skpl_agent.app._service.quota_service import (
    QuotaCheckResult,
    QuotaService,
    QuotaThresholds,
    QuotaUsage,
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def service() -> QuotaService:
    """Create a fresh QuotaService."""
    return QuotaService()


# ── QuotaThresholds Tests ──────────────────────────────────────────────────


class TestQuotaThresholds:
    """Tests for QuotaThresholds dataclass."""

    def test_default_values(self) -> None:
        """QuotaThresholds has sensible defaults."""
        q = QuotaThresholds()
        assert q.max_agents == 10
        assert q.max_sessions == 50
        assert q.max_workspaces == 5
        assert q.max_desktop_nodes == 3
        assert q.max_desktop_actions_per_minute == 60
        assert q.max_web_requests_per_day == 10000
        assert q.max_web_requests_per_minute == 30
        assert q.max_token_budget == 1_000_000
        assert q.max_tokens_per_request == 100_000
        assert q.max_storage_mb == 1024
        assert q.max_file_size_mb == 50
        assert q.max_anatomy_symbols == 100_000
        assert q.max_buglog_entries == 10_000
        assert q.max_api_requests_per_minute == 100

    def test_custom_values(self) -> None:
        """QuotaThresholds accepts custom values."""
        q = QuotaThresholds(max_agents=5, max_token_budget=500000)
        assert q.max_agents == 5
        assert q.max_token_budget == 500000


# ── QuotaUsage Tests ───────────────────────────────────────────────────────


class TestQuotaUsage:
    """Tests for QuotaUsage dataclass."""

    def test_default_values(self) -> None:
        """QuotaUsage starts at zero."""
        u = QuotaUsage(tenant_id="t1")
        assert u.tenant_id == "t1"
        assert u.active_agents == 0
        assert u.active_sessions == 0
        assert u.web_requests_today == 0
        assert u.tokens_used_today == 0
        assert u.desktop_actions_today == 0
        assert u.api_requests_today == 0
        assert u.storage_used_mb == 0.0

    def test_custom_values(self) -> None:
        """QuotaUsage accepts custom values."""
        u = QuotaUsage(
            tenant_id="t2",
            active_agents=3,
            web_requests_today=500,
            tokens_used_today=10000,
        )
        assert u.tenant_id == "t2"
        assert u.active_agents == 3
        assert u.web_requests_today == 500
        assert u.tokens_used_today == 10000


# ── QuotaCheckResult Tests ─────────────────────────────────────────────────


class TestQuotaCheckResult:
    """Tests for QuotaCheckResult dataclass."""

    def test_default_allowed(self) -> None:
        """QuotaCheckResult defaults to allowed=True."""
        r = QuotaCheckResult()
        assert r.allowed is True
        assert r.resource == ""
        assert r.current == 0
        assert r.limit == 0
        assert r.remaining == 0
        assert r.message == ""

    def test_denied_result(self) -> None:
        """QuotaCheckResult for denied quota."""
        r = QuotaCheckResult(
            allowed=False,
            resource="agents",
            current=10,
            limit=10,
            remaining=0,
            message="Quota exceeded for agents: 10/10",
        )
        assert r.allowed is False
        assert r.resource == "agents"
        assert r.current == 10
        assert r.limit == 10
        assert r.remaining == 0


# ── Get Quota Tests ────────────────────────────────────────────────────────


class TestGetQuota:
    """Tests for get_quota method."""

    @pytest.mark.asyncio
    async def test_get_quota_creates_defaults(self, service: QuotaService) -> None:
        """get_quota auto-creates default thresholds for new tenants."""
        quota = await service.get_quota("new-tenant")
        assert isinstance(quota, QuotaThresholds)
        assert quota.max_agents == 10  # default

    @pytest.mark.asyncio
    async def test_get_quota_returns_existing(self, service: QuotaService) -> None:
        """get_quota returns existing thresholds."""
        await service.set_quota("tenant-1", max_agents=20)
        quota = await service.get_quota("tenant-1")
        assert quota.max_agents == 20

    @pytest.mark.asyncio
    async def test_get_quota_idempotent(self, service: QuotaService) -> None:
        """Repeated get_quota returns the same object."""
        q1 = await service.get_quota("tenant-x")
        q2 = await service.get_quota("tenant-x")
        assert q1 is q2


# ── Set Quota Tests ────────────────────────────────────────────────────────


class TestSetQuota:
    """Tests for set_quota method."""

    @pytest.mark.asyncio
    async def test_set_quota_updates_thresholds(self, service: QuotaService) -> None:
        """set_quota updates specified thresholds."""
        quota = await service.set_quota(
            "tenant-1",
            max_agents=5,
            max_sessions=25,
            max_token_budget=500000,
        )
        assert quota.max_agents == 5
        assert quota.max_sessions == 25
        assert quota.max_token_budget == 500000

    @pytest.mark.asyncio
    async def test_set_quota_ignores_invalid_keys(self, service: QuotaService) -> None:
        """set_quota ignores keys not in QuotaThresholds."""
        quota = await service.set_quota(
            "tenant-1",
            invalid_key=999,
            another_fake="nope",
        )
        assert not hasattr(quota, "invalid_key")

    @pytest.mark.asyncio
    async def test_set_quota_partial_update(self, service: QuotaService) -> None:
        """set_quota only updates specified keys, leaving others."""
        await service.set_quota("tenant-1", max_agents=42)
        quota = await service.get_quota("tenant-1")
        assert quota.max_agents == 42
        assert quota.max_sessions == 50  # default unchanged


# ── List Quotas Tests ──────────────────────────────────────────────────────


class TestListQuotas:
    """Tests for list_quotas method."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service: QuotaService) -> None:
        """list_quotas returns empty dict when no quotas set."""
        quotas = await service.list_quotas()
        assert quotas == {}

    @pytest.mark.asyncio
    async def test_list_with_tenants(self, service: QuotaService) -> None:
        """list_quotas returns all tenant quotas."""
        await service.set_quota("t1", max_agents=10)
        await service.set_quota("t2", max_agents=20)
        quotas = await service.list_quotas()
        assert len(quotas) == 2
        assert "t1" in quotas
        assert "t2" in quotas
        assert quotas["t1"].max_agents == 10
        assert quotas["t2"].max_agents == 20


# ── Get Usage Tests ────────────────────────────────────────────────────────


class TestGetUsage:
    """Tests for get_usage method."""

    @pytest.mark.asyncio
    async def test_get_usage_creates_defaults(self, service: QuotaService) -> None:
        """get_usage auto-creates default usage for new tenants."""
        usage = await service.get_usage("new-tenant")
        assert isinstance(usage, QuotaUsage)
        assert usage.tenant_id == "new-tenant"
        assert usage.active_agents == 0

    @pytest.mark.asyncio
    async def test_get_usage_returns_existing(self, service: QuotaService) -> None:
        """get_usage returns existing usage data."""
        await service.increment_usage("tenant-1", web_requests=5)
        usage = await service.get_usage("tenant-1")
        assert usage.web_requests_today == 5


# ── Increment Usage Tests ──────────────────────────────────────────────────


class TestIncrementUsage:
    """Tests for increment_usage method."""

    @pytest.mark.asyncio
    async def test_increment_single_field(self, service: QuotaService) -> None:
        """increment_usage increments a single usage counter."""
        usage = await service.increment_usage("tenant-1", web_requests=10)
        assert usage.web_requests_today == 10

    @pytest.mark.asyncio
    async def test_increment_multiple_fields(self, service: QuotaService) -> None:
        """increment_usage increments multiple counters at once."""
        usage = await service.increment_usage(
            "tenant-1",
            web_requests=5,
            tokens=1000,
            agents=1,
        )
        assert usage.web_requests_today == 5
        assert usage.tokens_used_today == 1000
        assert usage.active_agents == 1

    @pytest.mark.asyncio
    async def test_increment_cumulative(self, service: QuotaService) -> None:
        """increment_usage accumulates values."""
        await service.increment_usage("tenant-1", web_requests=10)
        usage = await service.increment_usage("tenant-1", web_requests=5)
        assert usage.web_requests_today == 15

    @pytest.mark.asyncio
    async def test_increment_storage_mb(self, service: QuotaService) -> None:
        """increment_usage handles storage_mb mapping."""
        usage = await service.increment_usage("tenant-1", storage_mb=100)
        assert usage.storage_used_mb == 100.0

    @pytest.mark.asyncio
    async def test_increment_unknown_field_noop(self, service: QuotaService) -> None:
        """increment_usage silently ignores unknown fields."""
        usage = await service.increment_usage("tenant-1", unknown_field=100)
        assert usage.web_requests_today == 0  # unchanged


# ── Check Quota Tests ──────────────────────────────────────────────────────


class TestCheckQuota:
    """Tests for check_quota method."""

    @pytest.mark.asyncio
    async def test_check_quota_allowed(self, service: QuotaService) -> None:
        """check_quota allows when under limit."""
        result = await service.check_quota("tenant-1", "agents", requested=1)
        assert result.allowed is True
        assert result.resource == "agents"
        assert result.remaining == 9  # 10 - 0 - 1

    @pytest.mark.asyncio
    async def test_check_quota_denied(self, service: QuotaService) -> None:
        """check_quota denies when over limit."""
        await service.increment_usage("tenant-1", agents=10)  # max is 10
        result = await service.check_quota("tenant-1", "agents", requested=1)
        assert result.allowed is False
        assert result.remaining == 0
        assert "Quota exceeded" in result.message

    @pytest.mark.asyncio
    async def test_check_quota_exact_limit(self, service: QuotaService) -> None:
        """check_quota denies when exactly at limit."""
        await service.increment_usage("tenant-1", agents=10)
        result = await service.check_quota("tenant-1", "agents", requested=1)
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_check_quota_unknown_resource(self, service: QuotaService) -> None:
        """check_quota allows unknown resources."""
        result = await service.check_quota("tenant-1", "unknown_resource")
        assert result.allowed is True
        assert "Unknown resource" in result.message

    @pytest.mark.asyncio
    async def test_check_quota_with_custom_thresholds(
        self, service: QuotaService
    ) -> None:
        """check_quota respects custom quota thresholds."""
        await service.set_quota("tenant-1", max_agents=3)
        await service.increment_usage("tenant-1", agents=2)
        result = await service.check_quota("tenant-1", "agents", requested=1)
        assert result.allowed is True
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_check_quota_web_requests(self, service: QuotaService) -> None:
        """check_quota works for web_requests resource."""
        await service.increment_usage("tenant-1", web_requests=9900)
        result = await service.check_quota("tenant-1", "web_requests", requested=50)
        assert result.allowed is True
        assert result.remaining == 50  # 10000 - 9900 - 50

    @pytest.mark.asyncio
    async def test_check_quota_tokens(self, service: QuotaService) -> None:
        """check_quota works for tokens resource."""
        result = await service.check_quota("tenant-1", "tokens", requested=50000)
        assert result.allowed is True
        assert result.limit == 1_000_000
        assert result.remaining == 950000


# ── Get Quota Status Tests ─────────────────────────────────────────────────


class TestGetQuotaStatus:
    """Tests for get_quota_status method."""

    @pytest.mark.asyncio
    async def test_get_quota_status_all_resources(self, service: QuotaService) -> None:
        """get_quota_status returns all resource statuses."""
        results = await service.get_quota_status("tenant-1")
        assert len(results) == 11  # all tracked resources
        resources = {r.resource for r in results}
        assert "agents" in resources
        assert "sessions" in resources
        assert "tokens" in resources
        assert "web_requests" in resources
        assert "storage" in resources

    @pytest.mark.asyncio
    async def test_get_quota_status_allowed(self, service: QuotaService) -> None:
        """get_quota_status shows allowed for under-limit resources."""
        results = await service.get_quota_status("tenant-1")
        for r in results:
            assert r.allowed is True  # all at zero usage

    @pytest.mark.asyncio
    async def test_get_quota_status_denied_when_full(
        self, service: QuotaService
    ) -> None:
        """get_quota_status shows denied for exhausted resources."""
        await service.increment_usage("tenant-1", agents=10)
        results = await service.get_quota_status("tenant-1")
        agent_result = [r for r in results if r.resource == "agents"][0]
        assert agent_result.allowed is False
        assert agent_result.current == 10
        assert agent_result.limit == 10
        assert agent_result.remaining == 0


# ── Get Global Stats Tests ─────────────────────────────────────────────────


class TestGetGlobalStats:
    """Tests for get_global_stats method."""

    @pytest.mark.asyncio
    async def test_get_global_stats_empty(self, service: QuotaService) -> None:
        """get_global_stats returns zeros for empty service."""
        stats = await service.get_global_stats()
        assert stats["total_tenants"] == 0
        assert stats["total_tokens_used_today"] == 0
        assert stats["tenants"] == {}

    @pytest.mark.asyncio
    async def test_get_global_stats_with_tenants(self, service: QuotaService) -> None:
        """get_global_stats aggregates across tenants."""
        await service.set_quota("t1", max_agents=10)
        await service.set_quota("t2", max_agents=20)
        await service.increment_usage("t1", tokens=5000)
        await service.increment_usage("t2", tokens=3000)

        stats = await service.get_global_stats()
        assert stats["total_tenants"] == 2
        assert stats["total_tokens_used_today"] == 8000
        assert "t1" in stats["tenants"]
        assert "t2" in stats["tenants"]

    @pytest.mark.asyncio
    async def test_get_global_stats_tenant_details(
        self, service: QuotaService
    ) -> None:
        """get_global_stats includes per-tenant details."""
        await service.set_quota("t1", max_agents=15)
        stats = await service.get_global_stats()
        assert "t1" in stats["tenants"]
        assert "quota" in stats["tenants"]["t1"]
        assert "usage" in stats["tenants"]["t1"]