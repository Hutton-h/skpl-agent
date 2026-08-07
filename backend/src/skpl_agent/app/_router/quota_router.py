"""Quota management API router."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from skpl_agent.app._auth.router import _get_jwt_claims

from .._service.quota_service import QuotaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quota", tags=["Quota"])

async def _require_admin(request: Request):
    claims = await _get_jwt_claims(request)
    if claims.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return claims

_service: QuotaService | None = None


def _get_service() -> QuotaService:
    global _service
    if _service is None:
        _service = QuotaService()
    return _service


# ── Tenant Quota CRUD ────────────────────────────────────────────────


@router.get("/tenants/{tenant_id}", response_model=dict[str, Any])
async def get_tenant_quota(tenant_id: str, claims = Depends(_require_admin)) -> dict[str, Any]:
    """Get quota configuration for a tenant."""
    svc = _get_service()
    quota = await svc.get_quota(tenant_id)
    return {"tenant_id": tenant_id, "quota": vars(quota)}


@router.put("/tenants/{tenant_id}", response_model=dict[str, Any])
async def update_tenant_quota(
    tenant_id: str, body: dict[str, Any],
    claims = Depends(_require_admin),
) -> dict[str, Any]:
    """Update quota configuration for a tenant."""
    svc = _get_service()
    quota = await svc.set_quota(tenant_id, **body)
    return {"tenant_id": tenant_id, "quota": vars(quota)}


@router.get("/tenants", response_model=list[dict[str, Any]])
async def list_tenant_quotas(claims = Depends(_require_admin)) -> list[dict[str, Any]]:
    """List all tenant quotas."""
    svc = _get_service()
    quotas = await svc.list_quotas()
    return [
        {"tenant_id": tid, "quota": vars(q)}
        for tid, q in quotas.items()
    ]


# ── Usage ────────────────────────────────────────────────────────────


@router.get("/tenants/{tenant_id}/usage", response_model=dict[str, Any])
async def get_tenant_usage(tenant_id: str, claims = Depends(_require_admin)) -> dict[str, Any]:
    """Get current resource usage for a tenant."""
    svc = _get_service()
    usage = await svc.get_usage(tenant_id)
    return {"tenant_id": tenant_id, "usage": vars(usage)}


# ── Quota Check ──────────────────────────────────────────────────────


@router.get("/tenants/{tenant_id}/status", response_model=dict[str, Any])
async def get_quota_status(tenant_id: str, claims = Depends(_require_admin)) -> dict[str, Any]:
    """Get full quota status for all resources of a tenant."""
    svc = _get_service()
    results = await svc.get_quota_status(tenant_id)
    return {
        "tenant_id": tenant_id,
        "resources": [
            {
                "resource": r.resource,
                "allowed": r.allowed,
                "current": r.current,
                "limit": r.limit,
                "remaining": r.remaining,
                "message": r.message,
            }
            for r in results
        ],
    }


@router.post("/check", response_model=dict[str, Any])
async def check_resource_quota(body: dict[str, Any], claims = Depends(_require_admin)) -> dict[str, Any]:
    """Check if a tenant has remaining quota for a specific resource."""
    tenant_id = body.get("tenant_id", "default")
    resource = body.get("resource", "")
    requested = body.get("requested", 1)

    if not resource:
        raise HTTPException(status_code=400, detail="resource is required")

    svc = _get_service()
    result = await svc.check_quota(tenant_id, resource, requested)
    return {
        "tenant_id": tenant_id,
        "resource": result.resource,
        "allowed": result.allowed,
        "current": result.current,
        "limit": result.limit,
        "remaining": result.remaining,
        "message": result.message,
    }


# ── Stats ────────────────────────────────────────────────────────────


@router.get("/stats", response_model=dict[str, Any])
async def get_global_stats(claims = Depends(_require_admin)) -> dict[str, Any]:
    """Get global quota usage statistics."""
    svc = _get_service()
    return await svc.get_global_stats()