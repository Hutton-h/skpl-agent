"""SKPL Agent Code Generation (Agent-S CodeAgent Integration).

Provides secure code generation and execution capabilities adapted from
Agent-S. Supports Python and Bash code execution in isolated sandboxes,
with step-budgeted iterative refinement.

Architecture:
    CodeSandbox (abstract)
        ├── SubprocessSandbox  — subprocess-based isolation
        └── DockerSandbox      — (future) Docker-based isolation

    CodeAgent
        └── execute() — iterative code generation + execution loop
"""

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
from skpl_agent.code_generation._code_agent import (
    CodeAgent,
    CodeAgentConfig,
    CodeAgentResult,
)

__all__ = [
    # Code parsing
    "extract_code_block",
    "format_execution_result",
    "split_thinking_response",
    # Sandbox
    "CodeSandbox",
    "SubprocessSandbox",
    "ExecutionResult",
    # Agent
    "CodeAgent",
    "CodeAgentConfig",
    "CodeAgentResult",
]