"""Desktop automation REST API endpoints.

Provides endpoints for:
- Session management (create/list/delete)
- Screenshot capture
- UI tree extraction
- Action dispatch (click, type, scroll, hotkey, etc.)
- Action history
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from skpl_agent.app.deps import get_current_user_id
from skpl_agent.app._router._schema._desktop_automation import (
    ActionHistoryResponse,
    AvailableActionSchema,
    CreateSessionResponse,
    DispatchActionRequest,
    DispatchActionResponse,
    ExtractTreeRequest,
    ExtractTreeResponse,
    SessionResponse,
    TreeElementSchema,
)
from skpl_agent.app._service.desktop_automation_service import (
    DesktopAutomationService,
)

router = APIRouter(prefix="/api/desktop-automation", tags=["Desktop Automation"])

# Rename for consistent export
desktop_automation_router = router

# Singleton service instance (replaced by DI in production)
_service: DesktopAutomationService | None = None

# Session-to-user mapping for multi-tenant isolation
_session_owners: dict[str, str] = {}


def _get_service() -> DesktopAutomationService:
    global _service
    if _service is None:
        _service = DesktopAutomationService()
    return _service


# ── Session management ───────────────────────────────────────────────────

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    user_id: str = Depends(get_current_user_id),
) -> CreateSessionResponse:
    """Create a new desktop automation session."""
    svc = _get_service()
    session = await svc.create_session()
    _session_owners[session.session_id] = user_id
    return CreateSessionResponse(session_id=session.session_id, status=session.status)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
) -> list[SessionResponse]:
    """List all active automation sessions."""
    svc = _get_service()
    sessions = await svc.list_sessions()
    # Filter sessions owned by this user
    user_sessions = [s for s in sessions if _session_owners.get(s.session_id) == user_id]
    return [
        SessionResponse(
            session_id=s.session_id,
            status=s.status,
            action_count=len(s.action_history),
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in user_sessions
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    """Delete an automation session."""
    svc = _get_service()
    # Verify session belongs to this user
    if _session_owners.get(session_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied: session does not belong to this user")
    deleted = await svc.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


# ── Tree extraction ──────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/tree", response_model=ExtractTreeResponse)
async def extract_tree(
    session_id: str,
    body: ExtractTreeRequest = ExtractTreeRequest(),
    user_id: str = Depends(get_current_user_id),
) -> ExtractTreeResponse:
    """Extract the linearized UI accessibility tree for the current screen."""
    svc = _get_service()
    # Verify session belongs to this user
    if _session_owners.get(session_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied: session does not belong to this user")
    try:
        tree_text, elements = await svc.extract_tree(
            session_id, show_all=body.show_all
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ExtractTreeResponse(
        tree_text=tree_text,
        elements=[
            TreeElementSchema(
                element_id=e.element_id,
                role=e.role,
                title=e.title,
                text=e.text,
            )
            for e in elements
        ],
        element_count=len(elements),
    )


# ── Action dispatch ──────────────────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/actions",
    response_model=DispatchActionResponse,
)
async def dispatch_action(
    session_id: str,
    body: DispatchActionRequest,
    user_id: str = Depends(get_current_user_id),
) -> DispatchActionResponse:
    """Dispatch an action to the automation session."""
    svc = _get_service()
    # Verify session belongs to this user
    if _session_owners.get(session_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied: session does not belong to this user")
    try:
        result = await svc.dispatch_action(
            session_id, body.action_type, body.params
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return DispatchActionResponse(**result)


@router.get("/sessions/{session_id}/actions", response_model=ActionHistoryResponse)
async def get_action_history(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ActionHistoryResponse:
    """Get the action history for a session."""
    svc = _get_service()
    # Verify session belongs to this user
    if _session_owners.get(session_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied: session does not belong to this user")
    try:
        history = await svc.get_action_history(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ActionHistoryResponse(
        session_id=session_id,
        history=[DispatchActionResponse(**h) for h in history],
    )


# ── Available actions ────────────────────────────────────────────────────

@router.get("/actions", response_model=list[AvailableActionSchema])
async def list_available_actions(
    user_id: str = Depends(get_current_user_id),
) -> list[AvailableActionSchema]:
    """List all available desktop automation actions."""
    svc = _get_service()
    actions = await svc.get_available_actions()
    return [AvailableActionSchema(**a) for a in actions]


# ── Screenshot ───────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/screenshot")
async def capture_screenshot(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict[str, str]:
    """Capture a screenshot and return base64-encoded PNG."""
    import base64

    svc = _get_service()
    # Verify session belongs to this user
    if _session_owners.get(session_id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied: session does not belong to this user")
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    screenshot = await svc.capture_screenshot()
    encoded = base64.b64encode(screenshot).decode("utf-8")
    return {"session_id": session_id, "image_base64": encoded, "format": "png"}