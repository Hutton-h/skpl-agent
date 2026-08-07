"""Code Generation service layer."""

from __future__ import annotations

import logging
from typing import Any

from skpl_agent.code_generation import (
    CodeAgent,
    CodeAgentConfig,
    CodeAgentResult,
    SubprocessSandbox,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class CodeGenerationService:
    """Service for code generation and execution."""

    def __init__(self) -> None:
        self._sandbox = SubprocessSandbox()
        self._agent = CodeAgent(
            CodeAgentConfig(sandbox=self._sandbox)
        )
        self._results: dict[str, CodeAgentResult] = {}

    async def execute(
        self,
        task: str,
        context: str = "",
        budget: int | None = None,
    ) -> dict[str, Any]:
        """Execute a code generation task."""
        agent = self._agent
        if budget is not None:
            agent = CodeAgent(
                CodeAgentConfig(budget=budget, sandbox=self._sandbox)
            )

        result = await agent.execute(task, context=context)
        self._results[result.task_id] = result

        return {
            "task_id": result.task_id,
            "task_instruction": result.task_instruction,
            "completion_reason": result.completion_reason,
            "summary": result.summary,
            "steps_executed": result.steps_executed,
            "budget": result.budget,
            "duration_seconds": result.duration_seconds,
            "execution_history": result.execution_history,
        }

    async def get_result(self, task_id: str) -> dict[str, Any] | None:
        """Get a code generation result by task ID."""
        result = self._results.get(task_id)
        if not result:
            return None
        return {
            "task_id": result.task_id,
            "task_instruction": result.task_instruction,
            "completion_reason": result.completion_reason,
            "summary": result.summary,
            "steps_executed": result.steps_executed,
            "duration_seconds": result.duration_seconds,
        }

    async def list_results(self) -> list[dict[str, Any]]:
        """List all code generation results."""
        return [
            {
                "task_id": r.task_id,
                "task_instruction": r.task_instruction,
                "completion_reason": r.completion_reason,
                "steps_executed": r.steps_executed,
            }
            for r in self._results.values()
        ]

    async def run_python(self, code: str, timeout: int = 30) -> dict[str, Any]:
        """Execute Python code directly."""
        result = await self._sandbox.execute_python(code, timeout=timeout)
        return self._format_execution_result(result)

    async def run_bash(self, code: str, timeout: int = 30) -> dict[str, Any]:
        """Execute bash code directly."""
        result = await self._sandbox.execute_bash(code, timeout=timeout)
        return self._format_execution_result(result)

    @staticmethod
    def _format_execution_result(result: ExecutionResult) -> dict[str, Any]:
        return {
            "execution_id": result.execution_id,
            "status": result.status,
            "output": result.output,
            "error": result.error,
            "return_code": result.return_code,
            "duration_seconds": result.duration_seconds,
        }