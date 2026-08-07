"""Code parsing utilities.

Adapted from Agent-S gui_agents/s3/agents/code_agent.py.
Provides code block extraction, thinking/response splitting,
and execution result formatting.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_code_block(action: str) -> tuple[str | None, str | None]:
    """Extract code and determine type from an action string.

    Supports ```python, ```bash, and generic ``` blocks.

    Args:
        action: The raw action string from the LLM.

    Returns:
        (code_type, code) tuple. Both None if no code block found.
    """
    if "```python" in action:
        code_type = "python"
        code = action.split("```python")[1].split("```")[0].strip()
    elif "```bash" in action:
        code_type = "bash"
        code = action.split("```bash")[1].split("```")[0].strip()
    elif "```" in action:
        code_type = None
        code = action.split("```")[1].split("```")[0].strip()
    else:
        return None, None

    logger.debug("Extracted code block: type=%s, length=%d", code_type, len(code) if code else 0)
    return code_type, code


def split_thinking_response(response: str) -> tuple[str, str]:
    """Split a response into (action, thoughts) using XML-like tags.

    Expected format:
        <thoughts>...</thoughts>
        <answer>...code or DONE/FAIL...</answer>

    Args:
        response: The raw LLM response string.

    Returns:
        (action, thoughts) tuple.
    """
    thoughts = ""
    action = response.strip()

    if "<thoughts>" in response and "</thoughts>" in response:
        try:
            thoughts = response.split("<thoughts>")[1].split("</thoughts>")[0].strip()
        except (IndexError, ValueError):
            pass

    if "<answer>" in response and "</answer>" in response:
        try:
            action = response.split("<answer>")[1].split("</answer>")[0].strip()
        except (IndexError, ValueError):
            pass

    return action, thoughts


def format_execution_result(
    result: dict[str, Any], step_count: int
) -> str:
    """Format an execution result into a context string for the LLM.

    Args:
        result: The execution result dict with status, output, error, etc.
        step_count: The current step number (0-indexed).

    Returns:
        Formatted string for injection into the next LLM message.
    """
    if not result:
        return f"Step {step_count + 1} Error:\nError: No result returned from execution\n"

    status = result.get("status", "unknown")
    return_code = result.get("returncode", result.get("return_code", -1))
    output = result.get("output", "")
    error = result.get("error", "")

    parts = [
        f"Step {step_count + 1} Result:",
        f"Status: {status}",
        f"Return Code: {return_code}",
    ]
    if output:
        parts.append(f"Output:\n{output}")
    if error:
        parts.append(f"Error:\n{error}")

    return "\n".join(parts)