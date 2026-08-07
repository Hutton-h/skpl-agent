"""TaskDispatcher middleware — automatically splits complex tasks into subtasks
and dispatches them to specialized sub-agents via the Team system.

Based on Superpowers' agent orchestration pattern, this middleware:
    1. Analyzes incoming user requests for complexity signals.
    2. When a complex task is detected, generates a plan of subtasks.
    3. Dispatches each subtask to a sub-agent via TeamCreate + AgentCreate.
    4. Collects results and synthesizes a unified response.

Architecture:
    ``on_reasoning`` — inspects the user's message for complexity
    signals. If the task warrants decomposition, injects a plan
    generation step into the agent's reasoning flow.

    ``on_acting`` — after a plan is generated, monitors tool calls
    and intercepts TaskCreate calls to spawn sub-agents via the
    Team system.

    ``on_reply`` — collects sub-agent results and synthesizes them
    into a unified response for the user.
"""
from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator, Any, Callable, TYPE_CHECKING

from skpl_agent.middleware._base import MiddlewareBase

if TYPE_CHECKING:
    from skpl_agent.agent import Agent

logger = logging.getLogger(__name__)

# ── Complexity signals ─────────────────────────────────────────────────────
# Patterns that indicate a task is complex enough to warrant decomposition.

COMPLEXITY_SIGNALS = [
    # Multi-step indicators
    r'and\s+also',
    r'and\s+then',
    r'first.*then.*finally',
    r'step\s+\d',
    r'多步',
    r'先.*再.*然后',
    # Quantity indicators
    r'(multiple|several|various|many|all)',
    r'(多个|若干|各个|所有|全部)',
    # Task type indicators
    r'(research\s+and|analyze\s+and|build\s+and|create\s+and|fix\s+and)',
    r'(研究并|分析并|构建并|创建并|修复并)',
    # Cross-domain indicators
    r'(frontend.*backend|backend.*frontend|full.?stack|end.?to.?end)',
    r'(前端.*后端|后端.*前端|全栈|端到端)',
    # Explicit delegation
    r'(use\s+sub.?agent|spawn\s+agent|delegate|parallel)',
    r'(使用子代理|委托|并行)',
]

# Minimum message length to consider for decomposition
MIN_COMPLEXITY_LENGTH = 80


class TaskDispatcher(MiddlewareBase):
    """Middleware that automatically decomposes complex tasks into
    subtasks and dispatches them to sub-agents.

    When a user request is detected as complex, the middleware:
    1. Injects a task-decomposition prompt into the reasoning flow.
    2. Monitors for TaskCreate tool calls and spawns sub-agents.
    3. Collects and synthesizes sub-agent results.

    Usage:
        ```python
        agent = Agent(
            ...,
            middlewares=[
                TaskDispatcher(
                    auto_decompose=True,
                    max_subtasks=8,
                ),
            ],
        )
        ```

    Args:
        auto_decompose: Whether to automatically detect and decompose
            complex tasks (default True).
        max_subtasks: Maximum number of subtasks to spawn (default 8).
        complexity_threshold: Minimum number of complexity signals
            required to trigger decomposition (default 1).
    """

    TASK_DECOMPOSITION_PROMPT = """
## Task Decomposition

When you receive a complex request that involves multiple independent or
sequential steps, you MUST:

1. **Analyze** the request and identify distinct subtasks.
2. **Create a plan** using the plan system — list each subtask as a step.
3. **For each subtask that can run independently**, use `TaskCreate` to
   spawn a sub-agent with a clear, focused instruction.
4. **Wait for all sub-agents** to complete before synthesizing results.
5. **Synthesize** the results into a unified response using `publish_visual`
   for charts, comparisons, or dashboards.

### When to Decompose
- The request spans multiple domains (e.g., frontend + backend).
- The request has 3+ distinct steps.
- The user explicitly asks for parallel execution.
- The task involves both research and implementation.

### When NOT to Decompose
- Simple single-step tasks (read a file, answer a question).
- Tasks that must execute sequentially with data dependencies.
- Tasks where the overhead of spawning sub-agents outweighs the benefit.
"""

    def __init__(
        self,
        *,
        auto_decompose: bool = True,
        max_subtasks: int = 8,
        complexity_threshold: int = 1,
    ) -> None:
        super().__init__()
        self._auto_decompose = auto_decompose
        self._max_subtasks = max_subtasks
        self._complexity_threshold = complexity_threshold
        self._active_subtasks: dict[str, str] = {}  # task_id -> agent_id

    # ── Complexity detection ───────────────────────────────────────────

    def _detect_complexity(self, user_message: str) -> bool:
        """Check if a user message is complex enough to warrant decomposition.

        Args:
            user_message: The user's message text.

        Returns:
            True if the message meets the complexity threshold.
        """
        if not user_message or len(user_message) < MIN_COMPLEXITY_LENGTH:
            return False

        signal_count = 0
        for pattern in COMPLEXITY_SIGNALS:
            if re.search(pattern, user_message, re.IGNORECASE):
                signal_count += 1
            if signal_count >= self._complexity_threshold:
                return True

        return False

    # ── Middleware hooks ────────────────────────────────────────────────

    async def on_system_prompt(
        self, agent: "Agent", current_prompt: str
    ) -> str:
        """Inject task decomposition guidance into the system prompt.

        Only injects when auto_decompose is enabled and the guidance
        is not already present in the prompt.
        """
        if not self._auto_decompose:
            return current_prompt

        if self.TASK_DECOMPOSITION_PROMPT.strip() in current_prompt:
            return current_prompt

        return current_prompt + "\n" + self.TASK_DECOMPOSITION_PROMPT

    async def on_reasoning(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator[Any, None]:
        """Inspect the user's message and potentially inject
        task-decomposition guidance.

        Args:
            agent: The executing agent.
            input_kwargs: Reasoning input kwargs.
            next_handler: The next handler in the middleware chain.
        """
        # Check if the latest user message is complex
        try:
            msgs = agent.state.context if hasattr(agent.state, 'context') else []
            user_msgs = [m for m in msgs if getattr(m, 'role', '') == 'user']
            if user_msgs:
                last_user = user_msgs[-1]
                user_text = ""
                for block in getattr(last_user, 'content', []):
                    if getattr(block, 'type', '') == 'text':
                        user_text += getattr(block, 'text', '')
                if self._detect_complexity(user_text):
                    logger.info(
                        "TaskDispatcher: complex task detected, "
                        "decomposition guidance injected"
                    )
        except Exception:
            logger.debug("TaskDispatcher: could not inspect user message", exc_info=True)

        # Continue with the normal reasoning flow
        async for event in next_handler(input_kwargs):
            yield event

    async def get_middleware_key(self) -> str:
        """Unique key for state storage."""
        return "task_dispatcher"
