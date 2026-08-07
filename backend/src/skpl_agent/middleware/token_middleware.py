"""
SKPL Token Middleware — Tracks and limits token usage per agent session.

Integrates with AgentScope's middleware system to:
- Track token usage per model call
- Enforce token budgets
- Detect wasteful token usage patterns
- Report token statistics

Works alongside ContextMiddleware for comprehensive session management.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Awaitable, Callable, TYPE_CHECKING

from skpl_agent.context.token_estimator import TokenEstimator
from skpl_agent.context.token_ledger import BudgetExceededError, TokenLedger
from skpl_agent.context.waste_detector import WasteDetector
from skpl_agent.context.event_emitter import ContextEventEmitter

if TYPE_CHECKING:
    from skpl_agent.agent import Agent
    from skpl_agent.model import ChatResponse

logger = logging.getLogger(__name__)


class TokenMiddleware:
    """Token tracking and budget enforcement middleware.

    Usage:
        agent = Agent(
            middlewares=[
                TokenMiddleware(token_budget=100000),
            ],
        )
    """

    def __init__(
        self,
        token_budget: int | None = None,
        model_name: str | None = None,
        waste_detection: bool = True,
        budget_enforcement: bool = True,
        encoding_name: str | None = None,
    ):
        self._token_budget = token_budget
        self._model_name = model_name
        self._waste_detection = waste_detection
        self._budget_enforcement = budget_enforcement
        self._estimator = TokenEstimator(encoding_name=encoding_name)
        self._ledger: TokenLedger | None = None
        self._waste_detector: WasteDetector | None = None
        self._emitter: ContextEventEmitter | None = None
        if waste_detection:
            self._waste_detector = WasteDetector()

    def _ensure_ledger(self, agent: "Agent") -> TokenLedger:
        if self._ledger is None:
            session_id = getattr(agent, "session_id", agent.name)
            self._ledger = TokenLedger(
                session_id=session_id,
                token_budget=self._token_budget,
                model_name=self._model_name,
            )
            self._emitter = ContextEventEmitter(agent)
        return self._ledger

    # -- Middleware Hooks --

    async def on_reasoning(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Track tokens during reasoning phase."""
        async for event in next_handler():
            # Track token usage from streaming events
            if hasattr(event, "usage"):
                usage = event.usage
                input_tokens = getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0)
                output_tokens = getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0)
                if input_tokens or output_tokens:
                    self._ensure_ledger(agent).record(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model_name=getattr(event, "model", self._model_name),
                    )
            yield event

    async def on_model_call(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., Awaitable["ChatResponse"]],
    ) -> "ChatResponse":
        """Track token usage and enforce budget on model calls."""
        # Check budget before making the call
        if self._budget_enforcement:
            ledger = self._ensure_ledger(agent)
            usage_pct = ledger.budget_used_pct()

            # Emit warning at 80% usage
            if usage_pct >= 80 and usage_pct < 100 and self._emitter:
                await self._emitter.emit_token_budget_warning(
                    session_id=ledger.session_id,
                    budget=self._token_budget or 0,
                    used=ledger.total_tokens,
                    remaining=ledger.budget_remaining() or 0,
                    usage_pct=usage_pct,
                )

            if ledger.is_over_budget():
                budget = self._token_budget or 0
                used = ledger.total_tokens

                # Emit budget exceeded
                if self._emitter:
                    await self._emitter.emit_token_budget_exceeded(
                        session_id=ledger.session_id,
                        budget=budget,
                        used=used,
                    )

                raise BudgetExceededError(budget, used)

        # Estimate input tokens
        messages = input_kwargs.get("messages", [])
        input_text = ""
        for msg in messages:
            if hasattr(msg, "content"):
                input_text += str(msg.content)
        estimated_input = self._estimator.count(input_text)

        response = await next_handler()

        # Record token usage
        usage = getattr(response, "usage", None)
        if usage:
            input_tokens = getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0)
            self._ensure_ledger(agent).record(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=getattr(response, "model", self._model_name),
            )
        else:
            # Estimate from response content
            response_text = str(getattr(response, "content", ""))
            estimated_output = self._estimator.count(response_text)
            self._ensure_ledger(agent).record(
                input_tokens=estimated_input,
                output_tokens=estimated_output,
                model_name=getattr(response, "model", self._model_name),
            )

        return response

    async def on_acting(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Track tool output for waste detection."""
        tool_call = input_kwargs.get("tool_call")
        tool_name = getattr(tool_call, "name", "unknown") if tool_call else "unknown"

        tool_output = ""
        async for event in next_handler():
            if hasattr(event, "content"):
                tool_output += str(event.content)
            yield event

        # Check for duplicate outputs
        if self._waste_detector and tool_output:
            is_duplicate = self._waste_detector.record_tool_output(tool_name, tool_output)
            if is_duplicate:
                logger.info("Duplicate tool output detected for '%s'", tool_name)

                # Emit waste detected event
                if self._emitter:
                    ledger = self._ensure_ledger(agent)
                    await self._emitter.emit_token_waste_detected(
                        session_id=ledger.session_id,
                        pattern_type="duplicate_output",
                        severity="medium",
                        tokens_wasted=len(tool_output) // 4,
                        description=f"Duplicate output from tool '{tool_name}'",
                    )

    async def on_system_prompt(self, agent: "Agent", current_prompt: str) -> str:
        """Add token budget info to system prompt."""
        if self._ledger and self._token_budget:
            remaining = self._token_budget - self._ledger.total_tokens
            budget_info = (
                f"\n\n## Token Budget\n"
                f"Budget: {self._token_budget} tokens\n"
                f"Used: {self._ledger.total_tokens} tokens\n"
                f"Remaining: {remaining} tokens\n"
                f"Be efficient with your token usage."
            )
            return current_prompt + budget_info
        return current_prompt

    # -- Query Methods --

    def get_summary(self) -> dict | None:
        """Get token usage summary."""
        if self._ledger is None:
            return None
        summary = self._ledger.get_summary()
        return {
            "total_tokens": summary.total_tokens,
            "input_tokens": summary.total_input_tokens,
            "output_tokens": summary.total_output_tokens,
            "waste_tokens": summary.total_waste_tokens,
            "waste_rate": summary.waste_rate,
            "cost_usd": summary.total_cost_usd,
            "budget_used_pct": self._ledger.budget_used_pct(),
        }

    def get_waste_patterns(self) -> list:
        """Get detected waste patterns."""
        if self._waste_detector:
            return self._waste_detector.get_patterns()
        return []

    async def get_middleware_key(self) -> str:
        return "skpl_token_middleware"