"""Quota management service.

Manages per-tenant resource quotas, usage tracking, and enforcement.
Uses the ORM models TenantQuotaRow and ResourceUsageRow for persistence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QuotaThresholds:
    """Default quota thresholds for new tenants."""

    max_agents: int = 10
    max_sessions: int = 50
    max_workspaces: int = 5
    max_desktop_nodes: int = 3
    max_desktop_actions_per_minute: int = 60
    max_web_requests_per_day: int = 10000
    max_web_requests_per_minute: int = 30
    max_token_budget: int = 1_000_000
    max_tokens_per_request: int = 100_000
    max_storage_mb: int = 1024
    max_file_size_mb: int = 50
    max_anatomy_symbols: int = 100_000
    max_buglog_entries: int = 10_000
    max_api_requests_per_minute: int = 100


@dataclass
class QuotaUsage:
    """Current resource usage for a tenant."""

    tenant_id: str = ""
    active_agents: int = 0
    active_sessions: int = 0
    active_workspaces: int = 0
    registered_desktop_nodes: int = 0
    web_requests_today: int = 0
    tokens_used_today: int = 0
    desktop_actions_today: int = 0
    api_requests_today: int = 0
    storage_used_mb: float = 0.0
    anatomy_symbols_count: int = 0
    buglog_entries_count: int = 0


@dataclass
class QuotaCheckResult:
    """Result of a quota check."""

    allowed: bool = True
    resource: str = ""
    current: int = 0
    limit: int = 0
    remaining: int = 0
    message: str = ""


class QuotaService:
    """Service for managing tenant quotas and resource usage.

    In production, this would use the database-backed ORM models.
    For now, it uses in-memory storage with the same schema.
    """

    def __init__(self) -> None:
        self._quotas: dict[str, QuotaThresholds] = {}
        self._usage: dict[str, QuotaUsage] = {}

    # ── Quota Management ──────────────────────────────────────────────

    async def get_quota(self, tenant_id: str) -> QuotaThresholds:
        """Get quota thresholds for a tenant, creating defaults if needed."""
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = QuotaThresholds()
        return self._quotas[tenant_id]

    async def set_quota(self, tenant_id: str, **kwargs: Any) -> QuotaThresholds:
        """Update quota thresholds for a tenant."""
        quota = await self.get_quota(tenant_id)
        valid_keys = set(QuotaThresholds.__dataclass_fields__.keys())
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(quota, key, value)
        return quota

    async def list_quotas(self) -> dict[str, QuotaThresholds]:
        """List all tenant quotas."""
        return dict(self._quotas)

    # ── Usage Tracking ────────────────────────────────────────────────

    async def get_usage(self, tenant_id: str) -> QuotaUsage:
        """Get current resource usage for a tenant."""
        if tenant_id not in self._usage:
            self._usage[tenant_id] = QuotaUsage(tenant_id=tenant_id)
        usage = self._usage[tenant_id]

        # Auto-reset daily counters if needed
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if not hasattr(self, "_last_reset"):
            self._last_reset: dict[str, datetime] = {}
        last = self._last_reset.get(tenant_id)
        if last is None or last < today_start:
            usage.web_requests_today = 0
            usage.tokens_used_today = 0
            usage.desktop_actions_today = 0
            usage.api_requests_today = 0
            self._last_reset[tenant_id] = now

        return usage

    async def increment_usage(
        self,
        tenant_id: str,
        **kwargs: int,
    ) -> QuotaUsage:
        """Increment usage counters for a tenant."""
        usage = await self.get_usage(tenant_id)
        field_map = {
            "web_requests": "web_requests_today",
            "tokens": "tokens_used_today",
            "desktop_actions": "desktop_actions_today",
            "api_requests": "api_requests_today",
            "agents": "active_agents",
            "sessions": "active_sessions",
            "storage_mb": "storage_used_mb",
        }
        for key, count in kwargs.items():
            attr = field_map.get(key, key)
            if hasattr(usage, attr):
                current = getattr(usage, attr, 0)
                setattr(usage, attr, current + count)
        return usage

    # ── Quota Checking ────────────────────────────────────────────────

    async def check_quota(
        self,
        tenant_id: str,
        resource: str,
        requested: int = 1,
    ) -> QuotaCheckResult:
        """Check if a tenant has remaining quota for a resource."""
        quota = await self.get_quota(tenant_id)
        usage = await self.get_usage(tenant_id)

        resource_map: dict[str, tuple[str, str]] = {
            "agents": ("active_agents", "max_agents"),
            "sessions": ("active_sessions", "max_sessions"),
            "workspaces": ("active_workspaces", "max_workspaces"),
            "desktop_nodes": ("registered_desktop_nodes", "max_desktop_nodes"),
            "web_requests": ("web_requests_today", "max_web_requests_per_day"),
            "tokens": ("tokens_used_today", "max_token_budget"),
            "desktop_actions": ("desktop_actions_today", "max_desktop_actions_per_minute"),
            "api_requests": ("api_requests_today", "max_api_requests_per_minute"),
            "storage": ("storage_used_mb", "max_storage_mb"),
            "anatomy_symbols": ("anatomy_symbols_count", "max_anatomy_symbols"),
            "buglog_entries": ("buglog_entries_count", "max_buglog_entries"),
        }

        if resource not in resource_map:
            return QuotaCheckResult(
                allowed=True,
                resource=resource,
                message=f"Unknown resource: {resource}",
            )

        usage_attr, limit_attr = resource_map[resource]
        current = getattr(usage, usage_attr, 0)
        limit = getattr(quota, limit_attr, 0)
        remaining = limit - current - requested

        if remaining < 0:
            return QuotaCheckResult(
                allowed=False,
                resource=resource,
                current=current,
                limit=limit,
                remaining=0,
                message=f"Quota exceeded for {resource}: {current}/{limit} (requested {requested})",
            )

        return QuotaCheckResult(
            allowed=True,
            resource=resource,
            current=current,
            limit=limit,
            remaining=remaining,
            message=f"Quota OK: {current + requested}/{limit}",
        )

    async def get_quota_status(self, tenant_id: str) -> list[QuotaCheckResult]:
        """Get full quota status for all resources."""
        quota = await self.get_quota(tenant_id)
        usage = await self.get_usage(tenant_id)

        resources = [
            ("agents", usage.active_agents, quota.max_agents),
            ("sessions", usage.active_sessions, quota.max_sessions),
            ("workspaces", usage.active_workspaces, quota.max_workspaces),
            ("desktop_nodes", usage.registered_desktop_nodes, quota.max_desktop_nodes),
            ("web_requests", usage.web_requests_today, quota.max_web_requests_per_day),
            ("tokens", usage.tokens_used_today, quota.max_token_budget),
            ("desktop_actions", usage.desktop_actions_today, quota.max_desktop_actions_per_minute),
            ("api_requests", usage.api_requests_today, quota.max_api_requests_per_minute),
            ("storage", int(usage.storage_used_mb), quota.max_storage_mb),
            ("anatomy_symbols", usage.anatomy_symbols_count, quota.max_anatomy_symbols),
            ("buglog_entries", usage.buglog_entries_count, quota.max_buglog_entries),
        ]

        return [
            QuotaCheckResult(
                allowed=current < limit,
                resource=name,
                current=current,
                limit=limit,
                remaining=max(0, limit - current),
                message=f"{current}/{limit}",
            )
            for name, current, limit in resources
        ]

    # ── Stats ─────────────────────────────────────────────────────────

    async def get_global_stats(self) -> dict[str, Any]:
        """Get global quota usage statistics."""
        total_tenants = len(self._quotas)
        total_usage = sum(
            u.tokens_used_today for u in self._usage.values()
        )
        return {
            "total_tenants": total_tenants,
            "total_tokens_used_today": total_usage,
            "tenants": {
                tid: {
                    "quota": vars(q),
                    "usage": vars(self._usage.get(tid, QuotaUsage(tenant_id=tid))),
                }
                for tid, q in self._quotas.items()
            },
        }