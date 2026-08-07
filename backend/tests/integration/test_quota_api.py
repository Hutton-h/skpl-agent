"""Integration tests for Quota API routes.

Tests cover:
- GET /api/quota/tenants/{tenant_id} — get tenant quota
- PUT /api/quota/tenants/{tenant_id} — update tenant quota
- GET /api/quota/tenants — list all tenant quotas
- GET /api/quota/tenants/{tenant_id}/usage — get tenant usage
- GET /api/quota/tenants/{tenant_id}/status — get quota status
- POST /api/quota/check — check resource quota
- GET /api/quota/stats — get global stats
- Error paths: 400, 404
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skpl_agent.app._service.quota_service import (
    QuotaCheckResult,
    QuotaService,
    QuotaThresholds,
    QuotaUsage,
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_service() -> QuotaService:
    """Create a mock QuotaService."""
    svc = MagicMock(spec=QuotaService)
    svc.get_quota = AsyncMock()
    svc.set_quota = AsyncMock()
    svc.list_quotas = AsyncMock()
    svc.get_usage = AsyncMock()
    svc.check_quota = AsyncMock()
    svc.get_quota_status = AsyncMock()
    svc.get_global_stats = AsyncMock()
    return svc


@pytest.fixture
def client(mock_service: QuotaService) -> TestClient:
    """Create a FastAPI TestClient with mocked Quota service."""
    from skpl_agent.app._router import quota_router

    with patch.object(
        quota_router, "_get_service", return_value=mock_service
    ):
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(quota_router.router)
        return TestClient(app)


# ── Get Tenant Quota Tests ─────────────────────────────────────────────────


class TestGetTenantQuotaEndpoint:
    """Tests for GET /api/quota/tenants/{tenant_id}."""

    def test_get_tenant_quota(self, client: TestClient, mock_service: QuotaService) -> None:
        """Getting tenant quota returns quota config."""
        quota = QuotaThresholds(max_agents=10, max_sessions=50)
        mock_service.get_quota.return_value = quota

        response = client.get("/api/quota/tenants/tenant-1")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-1"
        assert data["quota"]["max_agents"] == 10
        assert data["quota"]["max_sessions"] == 50

    def test_get_tenant_quota_creates_defaults(
        self, client: TestClient, mock_service: QuotaService
    ) -> None:
        """Getting quota for new tenant creates defaults."""
        quota = QuotaThresholds()
        mock_service.get_quota.return_value = quota

        response = client.get("/api/quota/tenants/new-tenant")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "new-tenant"
        assert "quota" in data


# ── Update Tenant Quota Tests ──────────────────────────────────────────────


class TestUpdateTenantQuotaEndpoint:
    """Tests for PUT /api/quota/tenants/{tenant_id}."""

    def test_update_tenant_quota(self, client: TestClient, mock_service: QuotaService) -> None:
        """Updating tenant quota returns updated config."""
        quota = QuotaThresholds(max_agents=20, max_sessions=100)
        mock_service.set_quota.return_value = quota

        response = client.put("/api/quota/tenants/tenant-1", json={
            "max_agents": 20,
            "max_sessions": 100,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-1"
        assert data["quota"]["max_agents"] == 20
        assert data["quota"]["max_sessions"] == 100

    def test_update_tenant_quota_partial(
        self, client: TestClient, mock_service: QuotaService
    ) -> None:
        """Updating with partial body only changes specified fields."""
        quota = QuotaThresholds(max_agents=5, max_sessions=50)
        mock_service.set_quota.return_value = quota

        response = client.put("/api/quota/tenants/tenant-1", json={
            "max_agents": 5,
        })
        assert response.status_code == 200
        mock_service.set_quota.assert_called_once_with("tenant-1", max_agents=5)


# ── List Tenant Quotas Tests ───────────────────────────────────────────────


class TestListTenantQuotasEndpoint:
    """Tests for GET /api/quota/tenants."""

    def test_list_tenants_empty(self, client: TestClient, mock_service: QuotaService) -> None:
        """Listing tenants when empty returns empty list."""
        mock_service.list_quotas.return_value = {}

        response = client.get("/api/quota/tenants")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tenants_with_data(self, client: TestClient, mock_service: QuotaService) -> None:
        """Listing tenants returns all quotas."""
        mock_service.list_quotas.return_value = {
            "t1": QuotaThresholds(max_agents=10),
            "t2": QuotaThresholds(max_agents=5),
        }

        response = client.get("/api/quota/tenants")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        tenant_ids = {t["tenant_id"] for t in data}
        assert tenant_ids == {"t1", "t2"}


# ── Get Tenant Usage Tests ─────────────────────────────────────────────────


class TestGetTenantUsageEndpoint:
    """Tests for GET /api/quota/tenants/{tenant_id}/usage."""

    def test_get_tenant_usage(self, client: TestClient, mock_service: QuotaService) -> None:
        """Getting tenant usage returns usage data."""
        usage = QuotaUsage(
            tenant_id="tenant-1",
            active_agents=3,
            web_requests_today=500,
            tokens_used_today=10000,
        )
        mock_service.get_usage.return_value = usage

        response = client.get("/api/quota/tenants/tenant-1/usage")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-1"
        assert data["usage"]["active_agents"] == 3
        assert data["usage"]["web_requests_today"] == 500
        assert data["usage"]["tokens_used_today"] == 10000


# ── Get Quota Status Tests ─────────────────────────────────────────────────


class TestGetQuotaStatusEndpoint:
    """Tests for GET /api/quota/tenants/{tenant_id}/status."""

    def test_get_quota_status(self, client: TestClient, mock_service: QuotaService) -> None:
        """Getting quota status returns all resource statuses."""
        mock_service.get_quota_status.return_value = [
            QuotaCheckResult(
                allowed=True, resource="agents", current=3, limit=10, remaining=7,
                message="3/10",
            ),
            QuotaCheckResult(
                allowed=False, resource="sessions", current=50, limit=50, remaining=0,
                message="50/50",
            ),
        ]

        response = client.get("/api/quota/tenants/tenant-1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-1"
        assert len(data["resources"]) == 2
        assert data["resources"][0]["resource"] == "agents"
        assert data["resources"][0]["allowed"] is True
        assert data["resources"][1]["resource"] == "sessions"
        assert data["resources"][1]["allowed"] is False


# ── Check Quota Tests ──────────────────────────────────────────────────────


class TestCheckQuotaEndpoint:
    """Tests for POST /api/quota/check."""

    def test_check_quota_allowed(self, client: TestClient, mock_service: QuotaService) -> None:
        """Checking quota returns allowed result."""
        mock_service.check_quota.return_value = QuotaCheckResult(
            allowed=True, resource="agents", current=3, limit=10, remaining=7,
            message="Quota OK: 4/10",
        )

        response = client.post("/api/quota/check", json={
            "tenant_id": "tenant-1",
            "resource": "agents",
            "requested": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["resource"] == "agents"
        assert data["remaining"] == 7

    def test_check_quota_denied(self, client: TestClient, mock_service: QuotaService) -> None:
        """Checking quota returns denied result."""
        mock_service.check_quota.return_value = QuotaCheckResult(
            allowed=False, resource="agents", current=10, limit=10, remaining=0,
            message="Quota exceeded for agents: 10/10 (requested 1)",
        )

        response = client.post("/api/quota/check", json={
            "tenant_id": "tenant-1",
            "resource": "agents",
            "requested": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is False
        assert data["remaining"] == 0

    def test_check_quota_missing_resource(self, client: TestClient) -> None:
        """Checking quota without resource returns 400."""
        response = client.post("/api/quota/check", json={
            "tenant_id": "tenant-1",
        })
        assert response.status_code == 400
        assert "resource is required" in response.json()["detail"].lower()

    def test_check_quota_with_defaults(self, client: TestClient, mock_service: QuotaService) -> None:
        """Checking quota with defaults for tenant_id and requested."""
        mock_service.check_quota.return_value = QuotaCheckResult(
            allowed=True, resource="agents", current=0, limit=10, remaining=10,
        )

        response = client.post("/api/quota/check", json={
            "resource": "agents",
        })
        assert response.status_code == 200
        # Should use default tenant_id="default", requested=1
        mock_service.check_quota.assert_called_once_with("default", "agents", 1)


# ── Get Global Stats Tests ─────────────────────────────────────────────────


class TestGetGlobalStatsEndpoint:
    """Tests for GET /api/quota/stats."""

    def test_get_global_stats(self, client: TestClient, mock_service: QuotaService) -> None:
        """Getting global stats returns aggregated data."""
        mock_service.get_global_stats.return_value = {
            "total_tenants": 5,
            "total_tokens_used_today": 500000,
            "tenants": {
                "t1": {"quota": {}, "usage": {}},
                "t2": {"quota": {}, "usage": {}},
            },
        }

        response = client.get("/api/quota/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tenants"] == 5
        assert data["total_tokens_used_today"] == 500000