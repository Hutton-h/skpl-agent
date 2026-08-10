"""Update management REST API endpoints.

Provides endpoints for:
- Checking for upstream updates
- Merging upstream changes
- Managing tracked repositories
- Viewing update history
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from skpl_agent.app._auth.router import _get_jwt_claims

from skpl_agent.updates.service import UpdateService
from skpl_agent.updates.merger import MergeResult

router = APIRouter(prefix="/api/updates", tags=["Updates"])

async def _require_admin(request: Request):
    claims = await _get_jwt_claims(request)
    if claims.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return claims


async def _require_auth(request: Request):
    """Require authenticated user (any role) — for read-only endpoints."""
    return await _get_jwt_claims(request)

# Singleton service instance
_service: UpdateService | None = None


def get_update_service() -> UpdateService:
    """Get or create the update service singleton."""
    global _service
    if _service is None:
        _service = UpdateService()
    return _service


def set_update_service(service: UpdateService) -> None:
    """Set the update service instance (for testing/DI)."""
    global _service
    _service = service


# ── Status ───────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status(claims = Depends(_require_auth)) -> dict[str, Any]:
    """Get the current update service status."""
    svc = get_update_service()
    return await svc.get_status()


@router.get("/health")
async def health_check(claims = Depends(_require_auth)) -> dict[str, str]:
    """Simple health check."""
    return {"status": "ok", "component": "updates"}


# ── Check ────────────────────────────────────────────────────────────────

@router.post("/check")
async def check_now(claims = Depends(_require_admin)) -> dict[str, Any]:
    """Trigger an immediate update check."""
    svc = get_update_service()
    report = await svc.check_now()
    return {
        "checked_at": report.checked_at.isoformat(),
        "total_repos": report.total_repos,
        "repos_with_updates": report.repos_with_updates,
        "results": [
            {
                "repo": r.repo_name,
                "has_updates": r.has_updates,
                "commits_behind": r.commits_behind,
                "latest_tag": r.latest_tag,
                "breaking_changes": r.breaking_changes,
                "error": r.error,
                "checked_at": r.checked_at.isoformat(),
            }
            for r in report.results
        ],
    }


# ── Merge ────────────────────────────────────────────────────────────────

@router.post("/merge/{repo_name}")
async def merge_repo(repo_name: str, claims = Depends(_require_admin)) -> dict[str, Any]:
    """Merge upstream changes for a specific repository."""
    svc = get_update_service()
    result = await svc.merge_repo(repo_name)

    if result.status == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Merge failed: {result.error}",
        )

    return {
        "repo_name": result.repo_name,
        "status": result.status,
        "files_changed": result.files_changed,
        "files_added": result.files_added,
        "files_deleted": result.files_deleted,
        "conflicts": result.conflicts,
        "merged_at": result.merged_at.isoformat(),
    }


@router.post("/rollback/{repo_name}")
async def rollback_repo(repo_name: str, claims = Depends(_require_admin)) -> dict[str, Any]:
    """Rollback the last merge for a repository."""
    svc = get_update_service()
    success = await svc.rollback_repo(repo_name)
    return {"repo_name": repo_name, "rolled_back": success}


# ── Repositories ─────────────────────────────────────────────────────────

@router.get("/repos")
async def list_repos(claims = Depends(_require_admin)) -> list[dict[str, Any]]:
    """List all tracked upstream repositories."""
    svc = get_update_service()
    return await svc.list_repos()


@router.post("/repos")
async def add_repo(body: dict[str, Any], claims = Depends(_require_admin)) -> dict[str, Any]:
    """Add a new upstream repository to track."""
    name = body.get("name", "")
    url = body.get("url", "")
    branch = body.get("branch", "main")

    if not name or not url:
        raise HTTPException(
            status_code=400,
            detail="name and url are required",
        )

    svc = get_update_service()
    await svc.add_repo(name, url, branch)
    return {"name": name, "url": url, "branch": branch, "status": "added"}


@router.delete("/repos/{name}")
async def remove_repo(name: str, claims = Depends(_require_admin)) -> dict[str, Any]:
    """Remove an upstream repository from tracking."""
    svc = get_update_service()
    success = await svc.remove_repo(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Repo not found: {name}")
    return {"name": name, "status": "removed"}