"""Shared FastAPI dependencies for the agentscope app."""
import logging
from fastapi import Header, HTTPException, Query, Request, status
from .workspace_manager import WorkspaceManagerBase
from ._manager import BackgroundTaskManager, ChatRunRegistry, SchedulerManager
from ._service import ChatService, KnowledgeBaseService, ResourceAccessService, SessionService
from ._types import AgentMiddlewareFactory, AgentToolFactory
from .message_bus import MessageBus
from .rag.blob_store import BlobStoreBase
from .rag.knowledge_base_manager import KnowledgeBaseManagerBase
from .storage import StorageBase
from ..rag import ParserBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth mode sentinel for dual-mode transition
# ---------------------------------------------------------------------------

_SKPL_AUTH_MODE: str | None = None


def _get_auth_mode() -> str:
    """Lazy-load the auth mode from config (cached)."""
    global _SKPL_AUTH_MODE
    if _SKPL_AUTH_MODE is None:
        try:
            from skpl_agent.config import get_settings
            _SKPL_AUTH_MODE = get_settings().auth.mode
        except Exception:
            _SKPL_AUTH_MODE = "none"
    return _SKPL_AUTH_MODE


async def get_current_user_id(
    request: Request,
    x_user_id: str = Header(None, description="Caller's user ID via X-User-ID header."),
    user_id: str = Query(None, description="Fallback user ID for clients that cannot send custom headers (e.g. EventSource)."),
    token: str = Query(None, description="JWT token for clients that cannot send custom headers (e.g. EventSource)."),
) -> str:
    """Return the caller's user ID.

    Dual-mode authentication:
    - ``SKPL_AUTH_MODE=none`` (default): Uses X-User-ID header or
      user_id query parameter (backward compatible).
    - ``SKPL_AUTH_MODE=jwt``: Attempts JWT Bearer token first; falls
      back to X-User-ID header for compatibility during transition.
      Also accepts ``token`` query parameter for SSE connections.

    Args:
        request (`Request`): The incoming FastAPI request.
        x_user_id (`str | None`): Value of the ``X-User-ID`` header.
        user_id (`str | None`): Value of the ``user_id`` query param.
        token (`str | None`): JWT token as query param (for EventSource SSE).

    Returns:
        `str`: The authenticated user ID.

    Raises:
        `HTTPException`: 401 if no valid authentication is provided.
    """
    auth_mode = _get_auth_mode()

    if auth_mode == "jwt":
        # JWT mode: try Bearer token first
        jwt_bearer = getattr(request.app.state, "jwt_bearer", None)
        if jwt_bearer is not None:
            try:
                claims = await jwt_bearer(request)
                logger.debug("JWT authenticated user: %s", claims.sub)
                return claims.sub
            except HTTPException:
                # JWT failed — try token query parameter
                pass

        # Try token query parameter (for SSE EventSource)
        if token is not None and jwt_bearer is not None:
            try:
                # Manually validate the token from query param
                from ._security.jwt_auth import JWTService
                jwt_service: JWTService = getattr(request.app.state, "jwt_service", None)
                if jwt_service is not None:
                    claims = jwt_service.verify_token(token)
                    logger.debug("JWT authenticated via query param: %s", claims.sub)
                    return claims.sub
            except Exception:
                pass

        # JWT mode: NO fallback to X-User-ID -- strict JWT-only
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token.",
        )

    # None mode: X-User-ID header or user_id query param (backward compatible).
    # Also try JWT Bearer token if no X-User-ID is provided — this allows
    # the frontend (which sends JWT tokens) to work in "none" auth mode.
    uid = x_user_id or user_id
    if not uid:
        # Try JWT Bearer token as fallback
        jwt_bearer = getattr(request.app.state, "jwt_bearer", None)
        if jwt_bearer is not None:
            try:
                claims = await jwt_bearer(request)
                logger.debug("JWT authenticated user (none mode): %s", claims.sub)
                return claims.sub
            except HTTPException:
                pass
        # Try token query parameter (for SSE EventSource)
        if token is not None and jwt_bearer is not None:
            try:
                from ._security.jwt_auth import JWTService
                jwt_service: JWTService = getattr(request.app.state, "jwt_service", None)
                if jwt_service is not None:
                    claims = jwt_service.verify_token(token)
                    logger.debug("JWT authenticated via query param (none mode): %s", claims.sub)
                    return claims.sub
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-ID header or user_id query parameter is required.",
        )
    return uid

async def get_storage(request: Request) -> StorageBase:
    """Return the application-wide storage backend.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `StorageBase`: The storage instance stored in ``app.state``.
    """
    return request.app.state.storage

async def get_message_bus(request: Request) -> MessageBus:
    """Return the application-wide message bus.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `MessageBus`: The message bus instance stored in ``app.state``.
    """
    return request.app.state.message_bus

async def get_chat_service(request: Request) -> ChatService:
    """Return the application-wide chat service.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `ChatService`: The chat service instance stored in ``app.state``.
    """
    return request.app.state.chat_service

async def get_resource_access_service(request: Request) -> ResourceAccessService:
    """Return the application-wide resource access service.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `ResourceAccessService`:
            The access service stored in ``app.state`` — the single
            entry point routers should use to resolve
            credential / agent / knowledge base records.
    """
    return request.app.state.resource_access_service

async def get_session_service(request: Request) -> SessionService:
    """Return the application-wide session service.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `SessionService`: The session service instance stored in
        ``app.state``.
    """
    return request.app.state.session_service

async def get_chat_run_registry(request: Request) -> ChatRunRegistry:
    """Return the per-process chat-run registry.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `ChatRunRegistry`: The registry stored in ``app.state``.
    """
    return request.app.state.chat_run_registry

async def get_scheduler_manager(request: Request) -> SchedulerManager:
    """Return the application-wide scheduler manager.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `SchedulerManager`: The scheduler manager stored in ``app.state``.
    """
    return request.app.state.scheduler_manager

async def get_background_task_manager(request: Request) -> BackgroundTaskManager:
    """Return the application-wide background task manager.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `BackgroundTaskManager`: The background task manager stored in
        ``app.state``.
    """
    return request.app.state.background_task_manager

async def get_workspace_manager(request: Request) -> WorkspaceManagerBase:
    """Return the application-wide workspace manager.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `WorkspaceManagerBase`: The workspace manager stored in ``app.state``.
    """
    return request.app.state.workspace_manager

async def get_extra_agent_middlewares(request: Request) -> AgentMiddlewareFactory | None:
    """Return the caller-supplied agent middleware factory, if any.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `AgentMiddlewareFactory | None`: The factory passed to
        :func:`~agentscope.app.create_app`, or ``None`` if not configured.
    """
    return request.app.state.extra_agent_middlewares

async def get_extra_agent_tools(request: Request) -> AgentToolFactory | None:
    """Return the caller-supplied agent tool factory, if any.

    Args:
        request (`Request`): The incoming FastAPI request.

    Returns:
        `AgentToolFactory | None`: The factory passed to
        :func:`~agentscope.app.create_app`, or ``None`` if not configured.
    """
    return request.app.state.extra_agent_tools

async def get_knowledge_base_service(request: Request) -> KnowledgeBaseService:
    """Return the application-wide knowledge base service.

    Args:
        request (`Request`):
            The incoming FastAPI request.

    Returns:
        `KnowledgeBaseService`:
            The service stored in ``app.state``.

    Raises:
        `HTTPException`:
            ``503`` when the app was created without a
            ``knowledge_base_manager`` and therefore exposes no
            knowledge base endpoints.
    """
    service = getattr(request.app.state, 'knowledge_base_service', None)
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Knowledge base feature is disabled — pass a knowledge_base_manager to create_app() to enable it.')
    return service

async def get_knowledge_base_manager(request: Request) -> KnowledgeBaseManagerBase:
    """Return the application-wide knowledge base manager.

    Args:
        request (`Request`):
            The incoming FastAPI request.

    Returns:
        `KnowledgeBaseManagerBase`:
            The manager stored in ``app.state``.

    Raises:
        `HTTPException`:
            ``503`` when the app was created without a
            ``knowledge_base_manager``.
    """
    manager = getattr(request.app.state, 'knowledge_base_manager', None)
    if manager is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Knowledge base feature is disabled — pass a knowledge_base_manager to create_app() to enable it.')
    return manager

async def get_blob_store(request: Request) -> BlobStoreBase:
    """Return the application-wide blob store.

    Args:
        request (`Request`):
            The incoming FastAPI request.

    Returns:
        `BlobStoreBase`:
            The blob store instance stored in ``app.state``.

    Raises:
        `HTTPException`:
            ``503`` when no blob store is configured (e.g. the KB
            feature was disabled at app-creation time).
    """
    blob_store = getattr(request.app.state, 'blob_store', None)
    if blob_store is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Blob store is not configured — pass a knowledge_base_manager (and optionally a blob_store) to create_app() to enable knowledge base features.')
    return blob_store

async def get_knowledge_parsers(request: Request) -> list[ParserBase] | dict[str, ParserBase]:
    """Return the parser registry configured on the app.

    Args:
        request (`Request`):
            The incoming FastAPI request.

    Returns:
        `list[ParserBase] | dict[str, ParserBase]`:
            The parser registry stored in ``app.state.knowledge_parsers``
            — the same value the index worker uses to dispatch uploads.

    Raises:
        `HTTPException`:
            ``503`` when the KB feature is disabled (no parsers
            configured).
    """
    parsers = getattr(request.app.state, 'knowledge_parsers', None)
    if not parsers:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Knowledge base feature is disabled — pass a knowledge_base_manager to create_app() to enable it.')
    return parsers