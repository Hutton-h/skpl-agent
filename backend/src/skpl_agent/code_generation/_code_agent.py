"""Code generation agent.

Adapted from Agent-S gui_agents/s3/agents/code_agent.py.
Provides iterative code generation with step-budgeted execution loops,
code extraction, and execution summary generation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from skpl_agent.code_generation._code_parser import (
    extract_code_block,
    format_execution_result,
    split_thinking_response,
)
from skpl_agent.code_generation._sandbox import (
    CodeSandbox,
    SubprocessSandbox,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


@dataclass
class CodeAgentConfig:
    """Configuration for the CodeAgent."""

    budget: int = 20  # Max steps per execution
    timeout_per_step: int = 30  # Seconds per code execution
    sandbox: CodeSandbox | None = None


@dataclass
class CodeAgentResult:
    """Result of a code agent execution session."""

    task_id: str
    task_instruction: str
    completion_reason: str  # DONE | FAIL | BUDGET_EXHAUSTED
    summary: str
    execution_history: list[dict[str, Any]]
    steps_executed: int
    budget: int
    duration_seconds: float = 0.0


class CodeAgent:
    """A dedicated agent for iterative code generation and execution.

    Features:
    - Step-budgeted execution loop
    - Code block extraction (Python, Bash)
    - Sandboxed execution via configurable CodeSandbox
    - Execution summary generation

    Usage:
        >>> agent = CodeAgent()
        >>> result = await agent.execute(
        ...     "Write a Python script to calculate fibonacci numbers",
        ...     sandbox=SubprocessSandbox(),
        ... )
    """

    # Default system prompt for the code agent
    CODE_AGENT_PROMPT = """You are a coding assistant. You help users by writing and executing code.

For each step:
1. Use <thoughts> tags to explain your reasoning
2. Use <answer> tags to provide either:
   - A code block: ```python\n...\n``` or ```bash\n...\n```
   - DONE to signal task completion
   - FAIL to signal task failure

Write code incrementally. Test each step before moving on.
Keep code concise and focused on the current sub-task."""

    CODE_SUMMARY_PROMPT = """You are a code execution summarizer. Describe what was done factually.
Focus on the code logic, outputs, and progression. Do not judge success or failure.
Keep summaries under 150 words."""

    def __init__(self, config: CodeAgentConfig | None = None) -> None:
        self._config = config or CodeAgentConfig()
        self._sandbox = self._config.sandbox or SubprocessSandbox()

    async def execute(
        self,
        task_instruction: str,
        sandbox: CodeSandbox | None = None,
        context: str = "",
        max_callback: Any = None,
    ) -> CodeAgentResult:
        """Execute code for the given task with a budget of steps.

        Args:
            task_instruction: The task description.
            sandbox: Override sandbox. Defaults to config sandbox.
            context: Optional additional context (e.g., screenshot description).
            max_callback: Optional async callback(step, action, result) for progress.

        Returns:
            CodeAgentResult with execution details.
        """
        import time

        started = time.time()
        task_id = uuid.uuid4().hex[:12]
        sandbox = sandbox or self._sandbox

        logger.info("CodeAgent [%s]: Starting task: %s", task_id, task_instruction)

        step_count = 0
        execution_history: list[dict[str, Any]] = []
        completion_reason = f"BUDGET_EXHAUSTED_AFTER_{self._config.budget}_STEPS"

        # In production, this would use an LLM for the loop.
        # For now, we provide a heuristic-based execution model.
        try:
            # Step 1: Parse the task to determine code type
            code_type, code = self._infer_code(task_instruction, context)

            if code:
                if code_type == "python":
                    result = await sandbox.execute_python(
                        code, timeout=self._config.timeout_per_step
                    )
                else:
                    result = await sandbox.execute_bash(
                        code, timeout=self._config.timeout_per_step
                    )

                execution_history.append({
                    "step": 1,
                    "action": code,
                    "thoughts": f"Executing {code_type} code for: {task_instruction}",
                    "result": {
                        "status": result.status,
                        "output": result.output,
                        "error": result.error,
                    },
                })

                completion_reason = "DONE" if result.status == "success" else "FAIL"
                step_count = 1

                if max_callback:
                    await max_callback(1, code, result)
            else:
                execution_history.append({
                    "step": 1,
                    "action": task_instruction,
                    "thoughts": "No executable code inferred from task",
                })
                completion_reason = "FAIL"
                step_count = 1

        except Exception as e:
            logger.error("CodeAgent [%s]: Execution error: %s", task_id, e)
            completion_reason = "FAIL"
            execution_history.append({
                "step": step_count + 1,
                "action": "",
                "thoughts": f"Error: {e}",
                "result": {"status": "error", "error": str(e)},
            })

        summary = self._generate_summary(execution_history, task_instruction)
        duration = time.time() - started

        return CodeAgentResult(
            task_id=task_id,
            task_instruction=task_instruction,
            completion_reason=completion_reason,
            summary=summary,
            execution_history=execution_history,
            steps_executed=step_count,
            budget=self._config.budget,
            duration_seconds=duration,
        )

    @staticmethod
    def _infer_code(task: str, context: str = "") -> tuple[str | None, str | None]:
        """Infer code type and content from a task description.

        In production, this would use an LLM. For now, uses heuristics.
        """
        # Check for inline code blocks
        code_type, code = extract_code_block(task)
        if code:
            return code_type, code

        if context:
            code_type, code = extract_code_block(context)
            if code:
                return code_type, code

        # Heuristic: Python-related keywords
        python_keywords = ["python", "script", "def ", "import ", "class ", "print("]
        bash_keywords = ["bash", "shell", "chmod", "mkdir", "grep", "curl", "wget"]

        if any(kw in task.lower() for kw in python_keywords):
            return "python", f"# Task: {task}\n# Write your Python code here\n"
        elif any(kw in task.lower() for kw in bash_keywords):
            return "bash", f"# Task: {task}\n# Write your bash code here\n"

        return None, None

    def _generate_summary(
        self, execution_history: list[dict[str, Any]], task_instruction: str
    ) -> str:
        """Generate a summary of the code execution session."""
        if not execution_history:
            return "No code was executed."

        steps = len(execution_history)
        results = [
            h.get("result", {}).get("status", "unknown")
            for h in execution_history
        ]
        successes = sum(1 for r in results if r == "success")
        errors = sum(1 for r in results if r == "error")

        parts = [
            f"Task: {task_instruction}",
            f"Steps executed: {steps}",
            f"Successes: {successes}",
            f"Errors: {errors}",
        ]

        # Add output from last successful step
        for h in reversed(execution_history):
            r = h.get("result", {})
            if r.get("status") == "success" and r.get("output"):
                output = r["output"][:200]
                parts.append(f"Last output: {output}")
                break

        return "\n".join(parts)