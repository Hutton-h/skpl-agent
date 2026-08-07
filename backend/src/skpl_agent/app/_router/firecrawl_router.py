"""Firecrawl skill router — web crawling API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from skpl_agent.app.deps import get_current_user_id

from .._service.firecrawl_service import (
    CrawlRequest,
    CrawlResult,
    FirecrawlConfig,
    FirecrawlService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/firecrawl", tags=["Firecrawl"])

# Singleton service instance — created lazily
_service: FirecrawlService | None = None


def _get_service() -> FirecrawlService:
    global _service
    if _service is None:
        _service = FirecrawlService()
    return _service


# ── Crawl endpoints ──────────────────────────────────────────────────


@router.post("/crawl", response_model=dict[str, Any])
async def start_crawl(body: dict[str, Any], user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Start a new web crawl operation."""
    svc = _get_service()
    request = CrawlRequest(
        url=body["url"],
        mode=body.get("mode", "crawl"),
        max_pages=body.get("max_pages", 10),
        include_patterns=body.get("include_patterns", []),
        exclude_patterns=body.get("exclude_patterns", []),
        wait_for=body.get("wait_for", 0),
    )
    try:
        result = await svc.start_crawl(request)
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))

    return _crawl_to_dict(result)


@router.get("/crawl/{crawl_id}", response_model=dict[str, Any])
async def get_crawl_status(crawl_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get the status of a crawl operation."""
    svc = _get_service()
    result = await svc.get_crawl_status(crawl_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Crawl {crawl_id} not found")
    return _crawl_to_dict(result)


@router.get("/crawls", response_model=list[dict[str, Any]])
async def list_crawls(limit: int = Query(default=50, ge=1, le=200), user_id: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    """List recent crawl results."""
    svc = _get_service()
    results = await svc.list_crawls(limit=limit)
    return [_crawl_to_dict(r) for r in results]


@router.post("/crawl/{crawl_id}/cancel", response_model=dict[str, Any])
async def cancel_crawl(crawl_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Cancel an active crawl."""
    svc = _get_service()
    success = await svc.cancel_crawl(crawl_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Crawl {crawl_id} cannot be cancelled (not active)",
        )
    return {"success": True}


# ── Config endpoints ─────────────────────────────────────────────────


@router.get("/config", response_model=dict[str, Any])
async def get_config(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get current Firecrawl configuration."""
    svc = _get_service()
    config = svc.config
    return {
        "api_key": "***" if config.api_key else "",
        "api_endpoint": config.api_endpoint,
        "max_concurrent_crawls": config.max_concurrent_crawls,
        "rate_limit_per_minute": config.rate_limit_per_minute,
        "default_max_pages": config.default_max_pages,
        "timeout_seconds": config.timeout_seconds,
        "respect_robots_txt": config.respect_robots_txt,
        "user_agent": config.user_agent,
    }


@router.put("/config", response_model=dict[str, Any])
async def update_config(body: dict[str, Any], user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Update Firecrawl configuration."""
    svc = _get_service()
    config = await svc.update_config(**body)
    return {
        "api_key": "***" if config.api_key else "",
        "api_endpoint": config.api_endpoint,
        "max_concurrent_crawls": config.max_concurrent_crawls,
        "rate_limit_per_minute": config.rate_limit_per_minute,
        "default_max_pages": config.default_max_pages,
        "timeout_seconds": config.timeout_seconds,
        "respect_robots_txt": config.respect_robots_txt,
        "user_agent": config.user_agent,
    }


# ── Stats endpoint ───────────────────────────────────────────────────


@router.get("/stats", response_model=dict[str, Any])
async def get_stats(user_id: str = Depends(get_current_user_id)) -> dict[str, Any]:
    """Get Firecrawl usage statistics."""
    svc = _get_service()
    return await svc.get_stats()


# ── Helpers ──────────────────────────────────────────────────────────


def _crawl_to_dict(result: CrawlResult) -> dict[str, Any]:
    return {
        "id": result.id,
        "url": result.url,
        "status": result.status,
        "pages_crawled": result.pages_crawled,
        "pages_failed": result.pages_failed,
        "content": result.content,
        "error": result.error,
        "created_at": result.created_at.isoformat(),
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
    }