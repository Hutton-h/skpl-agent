"""Memory API routes — context retrieval, cross-device bridging."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from skpl_agent.app.deps import get_current_user_id

router = APIRouter(prefix="/api/memory", tags=["Memory"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class BridgeSessionRequest(BaseModel):
    """Bridge a session to a new device."""
    session_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1, max_length=128)


class MemoryContextResponse(BaseModel):
    """Assembled memory context for a session."""
    l1_memories: list[dict]
    l2_memories: list[dict]
    l3_memories: list[dict]
    cross_device_hint: dict | None
    total_tokens: int


class DeviceSessionsResponse(BaseModel):
    """Sessions associated with a device."""
    device_id: str
    sessions: list[dict]


class MemoryHealthResponse(BaseModel):
    """Health status of memory subsystems."""
    l1_cerebrum: bool
    l2_mem0: bool
    l3_knowledge: bool


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_memory_manager(request: Request):
    """Get the MemoryManager from app state."""
    mgr = getattr(request.app.state, "memory_manager", None)
    if mgr is None:
        raise HTTPException(
            status_code=503,
            detail="Memory manager is not configured",
        )
    return mgr


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/context", response_model=MemoryContextResponse)
async def get_context(
    user_id: str = Depends(get_current_user_id),
    session_id: str | None = None,
    device_id: str | None = None,
    mem_mgr=Depends(_get_memory_manager),
):
    """Assemble memory context for the current user/session.

    Called by the frontend before starting a chat to inject memory
    into the agent's system prompt.
    """
    return await mem_mgr.assemble_context(
        user_id=user_id,
        session_id=session_id,
        device_id=device_id,
    )


@router.post("/bridge")
async def bridge_session(
    body: BridgeSessionRequest,
    user_id: str = Depends(get_current_user_id),
    mem_mgr=Depends(_get_memory_manager),
):
    """Bridge a session to a new device.

    Allows the user to continue a conversation from another device.
    The session is associated with the device_id and memory context
    is assembled for the new device.
    """
    return await mem_mgr.bridge_session(
        user_id=user_id,
        session_id=body.session_id,
        device_id=body.device_id,
    )


@router.get("/devices/{device_id}/sessions")
async def list_device_sessions(
    device_id: str,
    user_id: str = Depends(get_current_user_id),
    mem_mgr=Depends(_get_memory_manager),
):
    """List all sessions associated with a specific device."""
    sessions = await mem_mgr.list_device_sessions(
        user_id=user_id,
        device_id=device_id,
    )
    return DeviceSessionsResponse(device_id=device_id, sessions=sessions)


@router.get("/health", response_model=MemoryHealthResponse)
async def memory_health(
    user_id: str = Depends(get_current_user_id),
    mem_mgr=Depends(_get_memory_manager),
):
    """Check the health of all memory subsystems."""
    return mem_mgr.health()