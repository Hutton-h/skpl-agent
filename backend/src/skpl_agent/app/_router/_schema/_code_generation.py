"""Request/response schemas for code generation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExecuteCodeRequest(BaseModel):
    task: str = Field(..., min_length=1, description="Task description or code to execute")
    context: str = Field("", description="Additional context")
    budget: int | None = Field(None, ge=1, le=100, description="Max steps")


class ExecuteCodeResponse(BaseModel):
    task_id: str
    task_instruction: str
    completion_reason: str
    summary: str
    steps_executed: int
    budget: int
    duration_seconds: float
    execution_history: list[dict]


class CodeResultResponse(BaseModel):
    task_id: str
    task_instruction: str
    completion_reason: str
    summary: str
    steps_executed: int
    duration_seconds: float


class CodeResultListItem(BaseModel):
    task_id: str
    task_instruction: str
    completion_reason: str
    steps_executed: int


class RunPythonRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Python code to execute")
    timeout: int = Field(30, ge=1, le=300, description="Timeout in seconds")


class RunBashRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Bash code to execute")
    timeout: int = Field(30, ge=1, le=300, description="Timeout in seconds")


class RunCodeResponse(BaseModel):
    execution_id: str
    status: str
    output: str
    error: str
    return_code: int
    duration_seconds: float