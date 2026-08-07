"""Web Intelligence REST API endpoints.

Provides endpoints for:
- Web search (multi-engine)
- Knowledge retrieval
- Multi-step research tasks
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from skpl_agent.app.deps import get_current_user_id

from skpl_agent.app._router._schema._web_intelligence import (
    KnowledgeRequest,
    KnowledgeResponse,
    ResearchRequest,
    ResearchResponse,
    ResearchStatusResponse,
    ResearchListItem,
    SearchRequest,
    SearchResponse,
    SearchResultSchema,
)
from skpl_agent.app._service.web_intelligence_service import (
    WebIntelligenceService,
)

router = APIRouter(prefix="/api/web-intelligence", tags=["Web Intelligence"])
web_intelligence_router = router

_service: WebIntelligenceService | None = None


def _get_service() -> WebIntelligenceService:
    global _service
    if _service is None:
        _service = WebIntelligenceService()
    return _service


# ── Search ───────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, user_id: str = Depends(get_current_user_id)) -> SearchResponse:
    """Search the web using the configured engine."""
    svc = _get_service()
    results = await svc.search(
        query=body.query,
        engine=body.engine,
        num_results=body.num_results,
    )
    return SearchResponse(
        query=body.query,
        results=[SearchResultSchema(**r) for r in results],
        total=len(results),
    )


# ── Knowledge Retrieval ──────────────────────────────────────────────────

@router.post("/knowledge", response_model=KnowledgeResponse)
async def retrieve_knowledge(body: KnowledgeRequest, user_id: str = Depends(get_current_user_id)) -> KnowledgeResponse:
    """Retrieve knowledge for a task instruction."""
    svc = _get_service()
    result = await svc.retrieve_knowledge(
        instruction=body.instruction,
        search_query=body.search_query,
        engine=body.engine,
    )
    return KnowledgeResponse(
        query=result["query"],
        results=[SearchResultSchema(**r) for r in result["results"]],
    )


# ── Research ─────────────────────────────────────────────────────────────

@router.post("/research", response_model=ResearchResponse)
async def start_research(body: ResearchRequest, user_id: str = Depends(get_current_user_id)) -> ResearchResponse:
    """Start a multi-step research task."""
    svc = _get_service()
    try:
        result = await svc.start_research(
            query=body.query,
            context=body.context,
            max_sources=body.max_sources,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ResearchResponse(
        task_id=result["task_id"],
        query=result["query"],
        synthesis=result["synthesis"],
        sources=[SearchResultSchema(**s) for s in result["sources"]],
        sub_queries_used=result["sub_queries_used"],
        iterations=result["iterations"],
        duration_seconds=result["duration_seconds"],
    )


@router.get("/research/{task_id}", response_model=ResearchStatusResponse)
async def get_research_status(task_id: str, user_id: str = Depends(get_current_user_id)) -> ResearchStatusResponse:
    """Get the status of a research task."""
    svc = _get_service()
    task = await svc.get_research_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")
    return ResearchStatusResponse(**task)


@router.get("/research", response_model=list[ResearchListItem])
async def list_research_tasks(user_id: str = Depends(get_current_user_id)) -> list[ResearchListItem]:
    """List all research tasks."""
    svc = _get_service()
    tasks = await svc.list_research_tasks()
    return [ResearchListItem(**t) for t in tasks]


# ── Engines ──────────────────────────────────────────────────────────────

@router.get("/engines")
async def list_engines(user_id: str = Depends(get_current_user_id)) -> dict[str, list[str]]:
    """List available search engines."""
    svc = _get_service()
    engines = await svc.get_available_engines()
    return {"engines": engines}