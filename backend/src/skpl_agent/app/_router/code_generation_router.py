"""Code Generation REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from skpl_agent.app.deps import get_current_user_id

from skpl_agent.app._router._schema._code_generation import (
    ExecuteCodeRequest,
    ExecuteCodeResponse,
    CodeResultResponse,
    CodeResultListItem,
    RunPythonRequest,
    RunBashRequest,
    RunCodeResponse,
)
from skpl_agent.app._service.code_generation_service import (
    CodeGenerationService,
)

router = APIRouter(prefix="/api/code-generation", tags=["Code Generation"])
code_generation_router = router

_service: CodeGenerationService | None = None


def _get_service() -> CodeGenerationService:
    global _service
    if _service is None:
        _service = CodeGenerationService()
    return _service


# ── Code execution ───────────────────────────────────────────────────────

@router.post("/execute", response_model=ExecuteCodeResponse)
async def execute_code(body: ExecuteCodeRequest, user_id: str = Depends(get_current_user_id)) -> ExecuteCodeResponse:
    """Execute a code generation task."""
    svc = _get_service()
    try:
        result = await svc.execute(
            task=body.task,
            context=body.context,
            budget=body.budget,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ExecuteCodeResponse(**result)


@router.get("/results/{task_id}", response_model=CodeResultResponse)
async def get_result(task_id: str, user_id: str = Depends(get_current_user_id)) -> CodeResultResponse:
    """Get a code generation result."""
    svc = _get_service()
    result = await svc.get_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return CodeResultResponse(**result)


@router.get("/results", response_model=list[CodeResultListItem])
async def list_results(user_id: str = Depends(get_current_user_id)) -> list[CodeResultListItem]:
    """List all code generation results."""
    svc = _get_service()
    results = await svc.list_results()
    return [CodeResultListItem(**r) for r in results]


# ── Direct execution ─────────────────────────────────────────────────────

@router.post("/run/python", response_model=RunCodeResponse)
async def run_python(body: RunPythonRequest, user_id: str = Depends(get_current_user_id)) -> RunCodeResponse:
    """Execute Python code directly."""
    svc = _get_service()
    result = await svc.run_python(code=body.code, timeout=body.timeout)
    return RunCodeResponse(**result)


@router.post("/run/bash", response_model=RunCodeResponse)
async def run_bash(body: RunBashRequest, user_id: str = Depends(get_current_user_id)) -> RunCodeResponse:
    """Execute bash code directly."""
    svc = _get_service()
    result = await svc.run_bash(code=body.code, timeout=body.timeout)
    return RunCodeResponse(**result)