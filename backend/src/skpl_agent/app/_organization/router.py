"""Organization API routes — create, list, manage members."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from skpl_agent.app.deps import get_current_user_id

router = APIRouter(prefix="/api/orgs", tags=["Organizations"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class UpdateOrgRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: str = Field(default="member", pattern="^(owner|admin|member)$")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|member)$")


class OrgResponse(BaseModel):
    id: str
    name: str
    description: str | None
    owner_id: str
    is_active: bool
    created_at: str | None
    updated_at: str | None


class OrgWithRoleResponse(OrgResponse):
    role: str
    joined_at: str | None


class MemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    username: str | None
    email: str | None
    role: str
    joined_at: str | None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_org_service(request: Request):
    """Get the OrgService from app state."""
    svc = getattr(request.app.state, "org_service", None)
    if svc is None:
        raise HTTPException(
            status_code=503,
            detail="Organization service is not configured",
        )
    return svc


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/", response_model=OrgResponse)
async def create_org(
    body: CreateOrgRequest,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Create a new organization. The creator becomes the owner."""
    try:
        return await org_svc.create_org(
            name=body.name,
            owner_id=user_id,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/", response_model=list[OrgWithRoleResponse])
async def list_my_orgs(
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """List all organizations the current user belongs to."""
    return await org_svc.list_user_orgs(user_id)


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: str,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Get organization details by ID."""
    org = await org_svc.get_org(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: str,
    body: UpdateOrgRequest,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Update organization name or description."""
    org = await org_svc.update_org(
        org_id=org_id,
        name=body.name,
        description=body.description,
    )
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.delete("/{org_id}")
async def delete_org(
    org_id: str,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Deactivate (soft-delete) an organization."""
    deleted = await org_svc.delete_org(org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"status": "deactivated", "org_id": org_id}


# ── Members ───────────────────────────────────────────────────────────────


@router.post("/{org_id}/members", response_model=MemberResponse)
async def add_member(
    org_id: str,
    body: AddMemberRequest,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Add a member to an organization."""
    try:
        return await org_svc.add_member(
            org_id=org_id,
            user_id=body.user_id,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: str,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """List all members of an organization."""
    return await org_svc.list_members(org_id)


@router.delete("/{org_id}/members/{member_user_id}")
async def remove_member(
    org_id: str,
    member_user_id: str,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Remove a member from an organization."""
    try:
        removed = await org_svc.remove_member(org_id, member_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"status": "removed", "org_id": org_id, "user_id": member_user_id}


@router.patch("/{org_id}/members/{member_user_id}", response_model=MemberResponse)
async def update_member_role(
    org_id: str,
    member_user_id: str,
    body: UpdateMemberRoleRequest,
    user_id: str = Depends(get_current_user_id),
    org_svc=Depends(_get_org_service),
):
    """Update a member's role."""
    result = await org_svc.update_member_role(
        org_id=org_id,
        user_id=member_user_id,
        role=body.role,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return result