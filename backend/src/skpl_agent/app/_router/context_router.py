"""
Context Router — API endpoints for SKPL context management.

Provides RESTful endpoints for:
- /contexts → Context generation and session management
- /contexts/{id}/anatomy → Anatomy scanning and symbol search
- /contexts/{id}/buglog → Bug logging and management
- /contexts/{id}/cerebrum → Memory management
- /contexts/{id}/tokens → Token tracking and waste detection
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from skpl_agent.app._manager._context_manager import ContextManager
from skpl_agent.app._manager._scan_task_manager import ScanTaskManager
from skpl_agent.app._router._schema._common import PaginationParams
from skpl_agent.app.deps import get_current_user_id
from skpl_agent.app._router._schema._context import (
    AnatomyStatsResponse,
    BugResponse,
    BugStatsResponse,
    ContextGenerationRequest,
    ContextGenerationResponse,
    LogBugRequest,
    MemoryResponse,
    MemoryStatsResponse,
    RememberRequest,
    ScanRequest,
    ScanStatusResponse,
    SessionContextSummaryResponse,
    SymbolResponse,
    SymbolSearchRequest,
    TokenSummaryResponse,
    UpdateBugStatusRequest,
    WastePatternResponse,
)

context_router = APIRouter(prefix="/contexts", tags=["contexts"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_context_manager(request: Request) -> ContextManager:
    """Get the ContextManager from app state."""
    ctx_mgr = request.app.state.context_manager
    if ctx_mgr is None:
        raise HTTPException(
            status_code=503,
            detail="Context manager not initialized",
        )
    return ctx_mgr


def get_scan_task_manager(request: Request) -> ScanTaskManager:
    """Get the ScanTaskManager from app state."""
    scan_mgr = request.app.state.scan_task_manager
    if scan_mgr is None:
        raise HTTPException(
            status_code=503,
            detail="Scan task manager not initialized",
        )
    return scan_mgr


# ---------------------------------------------------------------------------
# Context Generation
# ---------------------------------------------------------------------------


@context_router.post(
    "/{session_id}/generate",
    response_model=ContextGenerationResponse,
    summary="Generate context string for a session",
)
async def generate_context(
    session_id: str,
    request: ContextGenerationRequest = ContextGenerationRequest(),
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> ContextGenerationResponse:
    """Generate a context string containing anatomy, bugs, and memories."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    context_str = ctx.generate_context(
        include_anatomy=request.include_anatomy,
        include_bugs=request.include_bugs,
        include_memory=request.include_memory,
        max_anatomy_entries=request.max_anatomy_entries,
        max_bug_entries=request.max_bug_entries,
        max_memory_entries=request.max_memory_entries,
    )

    estimated_tokens = len(context_str) // 4 if context_str else 0
    return ContextGenerationResponse(context=context_str, estimated_tokens=estimated_tokens)


@context_router.get(
    "/{session_id}/summary",
    response_model=SessionContextSummaryResponse,
    summary="Get comprehensive session context summary",
)
async def get_session_summary(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> SessionContextSummaryResponse:
    """Get a comprehensive summary of all context subsystems."""
    ctx = await ctx_mgr.get_session_context(session_id)
    summary = ctx.get_summary()
    return SessionContextSummaryResponse(**summary)


# ---------------------------------------------------------------------------
# Anatomy Scanning
# ---------------------------------------------------------------------------


@context_router.post(
    "/{session_id}/anatomy/scan",
    response_model=ScanStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an anatomy scan",
)
async def start_scan(
    session_id: str,
    request: ScanRequest = ScanRequest(),
    scan_mgr: ScanTaskManager = Depends(get_scan_task_manager),
    user_id: str = Depends(get_current_user_id),
) -> ScanStatusResponse:
    """Start an async anatomy scan for the project."""
    from skpl_agent.context.anatomy_scanner import ScanMode

    mode = ScanMode.FULL if request.mode == "full" else ScanMode.INCREMENTAL
    task_id = await scan_mgr.submit(
        root_path=request.root_path,
        mode=mode,
        changed_files=request.changed_files,
    )

    status = scan_mgr.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=500, detail="Failed to create scan task")

    return ScanStatusResponse(**status)


@context_router.get(
    "/{session_id}/anatomy/scan/{task_id}",
    response_model=ScanStatusResponse,
    summary="Get scan task status",
)
async def get_scan_status(
    session_id: str,
    task_id: str,
    scan_mgr: ScanTaskManager = Depends(get_scan_task_manager),
    user_id: str = Depends(get_current_user_id),
) -> ScanStatusResponse:
    """Get the status of an async scan task."""
    status = scan_mgr.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Scan task not found")

    result = None
    scan_result = scan_mgr.get_result(task_id)
    if scan_result:
        result = {
            "files_scanned": scan_result.total_files_scanned,
            "symbols_extracted": scan_result.total_symbols_extracted,
            "duration_seconds": scan_result.duration_seconds,
            "languages": scan_result.languages_found,
            "errors": scan_result.errors[:10],
        }

    error = scan_mgr.get_error(task_id)

    return ScanStatusResponse(**status, result=result, error=error)


@context_router.post(
    "/{session_id}/anatomy/search",
    response_model=list[SymbolResponse],
    summary="Search anatomy symbols",
)
async def search_symbols(
    session_id: str,
    request: SymbolSearchRequest,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> list[SymbolResponse]:
    """Search for symbols in the anatomy store."""
    ctx = await ctx_mgr.get_session_context(session_id)
    store = ctx.scanner.store
    results = store.search_symbols(
        query=request.query,
        language=request.language,
        kind=request.kind,
        limit=request.limit,
    )
    return [SymbolResponse(**r) for r in results]


@context_router.get(
    "/{session_id}/anatomy/stats",
    response_model=AnatomyStatsResponse,
    summary="Get anatomy store statistics",
)
async def get_anatomy_stats(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> AnatomyStatsResponse:
    """Get statistics about the anatomy store."""
    ctx = await ctx_mgr.get_session_context(session_id)
    store = ctx.scanner.store
    stats = store.get_stats()
    return AnatomyStatsResponse(**stats)


# ---------------------------------------------------------------------------
# Bug Log
# ---------------------------------------------------------------------------


@context_router.post(
    "/{session_id}/buglog",
    response_model=BugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a bug",
)
async def log_bug(
    session_id: str,
    request: LogBugRequest,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> BugResponse:
    """Log a bug encountered during agent execution."""
    ctx = await ctx_mgr.get_session_context(session_id)
    bug = ctx.log_bug(
        error_type=request.error_type,
        error_message=request.error_message,
        error_traceback=request.error_traceback,
        file_path=request.file_path,
        line_number=request.line_number,
    )

    return BugResponse(
        id=bug.id,
        session_id=bug.session_id,
        agent_id=bug.agent_id,
        error_type=bug.error_type,
        error_message=bug.error_message,
        error_traceback=bug.error_traceback,
        file_path=bug.file_path,
        line_number=bug.line_number,
        fingerprint=bug.fingerprint,
        duplicate_of=bug.duplicate_of,
        status=bug.status,
        resolution=bug.resolution,
        resolved_at=bug.resolved_at.isoformat() if bug.resolved_at else None,
        created_at=bug.created_at.isoformat(),
        updated_at=bug.updated_at.isoformat(),
    )


@context_router.get(
    "/{session_id}/buglog",
    response_model=list[BugResponse],
    summary="List recent bugs",
)
async def list_bugs(
    session_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> list[BugResponse]:
    """List recent bugs for a session."""
    ctx = await ctx_mgr.get_session_context(session_id)
    bugs = ctx.get_recent_bugs(limit)

    if status_filter:
        bugs = [b for b in bugs if b.status == status_filter]

    return [
        BugResponse(
            id=b.id,
            session_id=b.session_id,
            agent_id=b.agent_id,
            error_type=b.error_type,
            error_message=b.error_message,
            error_traceback=b.error_traceback,
            file_path=b.file_path,
            line_number=b.line_number,
            fingerprint=b.fingerprint,
            duplicate_of=b.duplicate_of,
            status=b.status,
            resolution=b.resolution,
            resolved_at=b.resolved_at.isoformat() if b.resolved_at else None,
            created_at=b.created_at.isoformat(),
            updated_at=b.updated_at.isoformat(),
        )
        for b in bugs
    ]


@context_router.patch(
    "/{session_id}/buglog/{bug_id}",
    response_model=BugResponse,
    summary="Update bug status",
)
async def update_bug_status(
    session_id: str,
    bug_id: str,
    request: UpdateBugStatusRequest,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> BugResponse:
    """Update a bug's status."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    from skpl_agent.context.buglog import BugStatus

    status_enum = BugStatus(request.status)
    bug = ctx.buglog.update_status(bug_id, status_enum, request.resolution)
    if bug is None:
        raise HTTPException(status_code=404, detail="Bug not found")

    return BugResponse(
        id=bug.id,
        session_id=bug.session_id,
        agent_id=bug.agent_id,
        error_type=bug.error_type,
        error_message=bug.error_message,
        fingerprint=bug.fingerprint,
        status=bug.status,
        resolution=bug.resolution,
        resolved_at=bug.resolved_at.isoformat() if bug.resolved_at else None,
        created_at=bug.created_at.isoformat(),
        updated_at=bug.updated_at.isoformat(),
    )


@context_router.get(
    "/{session_id}/buglog/stats",
    response_model=BugStatsResponse,
    summary="Get bug statistics",
)
async def get_bug_stats(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> BugStatsResponse:
    """Get bug statistics for a session."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stats = ctx.buglog.get_stats()
    return BugStatsResponse(**stats)


# ---------------------------------------------------------------------------
# Cerebrum (Memory)
# ---------------------------------------------------------------------------


@context_router.post(
    "/{session_id}/cerebrum",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a memory",
)
async def remember(
    session_id: str,
    request: RememberRequest,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> MemoryResponse:
    """Store a memory in the cerebrum."""
    ctx = await ctx_mgr.get_session_context(session_id)
    mem = ctx.remember(
        key=request.key,
        value=request.value,
        category=request.category,
        confidence=request.confidence,
    )

    return MemoryResponse(
        id=mem.id,
        key=mem.key,
        value=mem.value,
        category=mem.category,
        confidence=mem.confidence,
        ttl_seconds=mem.ttl_seconds,
        access_count=mem.access_count,
        last_accessed_at=mem.last_accessed_at.isoformat() if mem.last_accessed_at else None,
        created_at=mem.created_at.isoformat(),
        updated_at=mem.updated_at.isoformat(),
    )


@context_router.get(
    "/{session_id}/cerebrum",
    response_model=list[MemoryResponse],
    summary="List all memories",
)
async def list_memories(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> list[MemoryResponse]:
    """List all memories for a session."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    memories = ctx.cerebrum.get_all()
    return [
        MemoryResponse(
            id=m.id,
            key=m.key,
            value=m.value,
            category=m.category,
            confidence=m.confidence,
            ttl_seconds=m.ttl_seconds,
            access_count=m.access_count,
            last_accessed_at=m.last_accessed_at.isoformat() if m.last_accessed_at else None,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
        )
        for m in memories
    ]


@context_router.get(
    "/{session_id}/cerebrum/stats",
    response_model=MemoryStatsResponse,
    summary="Get memory statistics",
)
async def get_memory_stats(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> MemoryStatsResponse:
    """Get memory statistics for a session."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stats = ctx.cerebrum.get_stats()
    return MemoryStatsResponse(**stats)


@context_router.get(
    "/{session_id}/cerebrum/{key}",
    response_model=MemoryResponse,
    summary="Recall a memory",
)
async def recall(
    session_id: str,
    key: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> MemoryResponse:
    """Retrieve a memory by key."""
    ctx = await ctx_mgr.get_session_context(session_id)
    mem = ctx.recall(key)
    if mem is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryResponse(
        id=mem.id,
        key=mem.key,
        value=mem.value,
        category=mem.category,
        confidence=mem.confidence,
        ttl_seconds=mem.ttl_seconds,
        access_count=mem.access_count,
        last_accessed_at=mem.last_accessed_at.isoformat() if mem.last_accessed_at else None,
        created_at=mem.created_at.isoformat(),
        updated_at=mem.updated_at.isoformat(),
    )


@context_router.delete(
    "/{session_id}/cerebrum/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Forget a memory",
)
async def forget(
    session_id: str,
    key: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Remove a memory by key."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if not ctx.forget(key):
        raise HTTPException(status_code=404, detail="Memory not found")


@context_router.patch(
    "/{session_id}/cerebrum/{key}",
    response_model=MemoryResponse,
    summary="Update a memory",
)
async def update_memory(
    session_id: str,
    key: str,
    request: RememberRequest,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> MemoryResponse:
    """Update an existing memory's value, category, or confidence."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    mem = ctx.cerebrum.update(
        key=key,
        value=request.value,
        confidence=request.confidence,
        category=request.category,
    )
    if mem is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryResponse(
        id=mem.id,
        key=mem.key,
        value=mem.value,
        category=mem.category,
        confidence=mem.confidence,
        ttl_seconds=mem.ttl_seconds,
        access_count=mem.access_count,
        last_accessed_at=mem.last_accessed_at.isoformat() if mem.last_accessed_at else None,
        created_at=mem.created_at.isoformat(),
        updated_at=mem.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Token Tracking
# ---------------------------------------------------------------------------


@context_router.get(
    "/{session_id}/tokens",
    response_model=TokenSummaryResponse,
    summary="Get token usage summary",
)
async def get_token_summary(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> TokenSummaryResponse:
    """Get token usage summary for a session."""
    ctx = await ctx_mgr.get_session_context(session_id)
    summary = ctx.get_token_summary()

    return TokenSummaryResponse(
        session_id=summary.session_id,
        total_input_tokens=summary.total_input_tokens,
        total_output_tokens=summary.total_output_tokens,
        total_tokens=summary.total_tokens,
        total_waste_tokens=summary.total_waste_tokens,
        waste_rate=summary.waste_rate,
        total_cost_usd=summary.total_cost_usd,
        entry_count=summary.entry_count,
        model_breakdown=summary.model_breakdown,
        provider_breakdown=summary.provider_breakdown,
    )


@context_router.get(
    "/{session_id}/tokens/waste",
    response_model=list[WastePatternResponse],
    summary="Get waste detection patterns",
)
async def get_waste_patterns(
    session_id: str,
    ctx_mgr: ContextManager = Depends(get_context_manager),
    user_id: str = Depends(get_current_user_id),
) -> list[WastePatternResponse]:
    """Get detected waste patterns for a session."""
    ctx = await ctx_mgr.get_session_context(session_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Session not found")

    patterns = ctx.get_waste_patterns()
    return [
        WastePatternResponse(
            pattern_type=p.pattern_type,
            severity=p.severity,
            description=p.description,
            tokens_wasted=p.tokens_wasted,
            file_path=p.file_path,
            detected_at=p.detected_at.isoformat() if p.detected_at else None,
        )
        for p in patterns
    ]