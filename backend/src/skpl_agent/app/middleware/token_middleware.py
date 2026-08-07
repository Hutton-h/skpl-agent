"""Token tracking middleware for AgentScope.

Intercepts agent invocations to record token usage, enforce budget limits,
and detect waste patterns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from skpl_agent.context.token_estimator import TokenEstimator, estimate_tokens
from skpl_agent.context.waste_detector import WasteDetector, WastePattern

if TYPE_CHECKING:
    from skpl_agent.context.token_ledger import TokenLedger

logger = logging.getLogger(__name__)


class TokenMiddleware:
    """Middleware that tracks token usage across agent invocations.

    Records token consumption, checks budget limits, and identifies
    wasteful patterns like repeated reads or overly verbose contexts.
    """

    def __init__(
        self,
        token_ledger: TokenLedger | None = None,
        *,
        budget_limit: int | None = None,
        waste_detection: bool = True,
        estimator: TokenEstimator | None = None,
    ) -> None:
        self._ledger = token_ledger
        self._budget_limit = budget_limit
        self._waste_detection = waste_detection
        self._estimator = estimator or TokenEstimator()
        self._waste_detector = WasteDetector() if waste_detection else None
        self._recent_contents: list[str] = []

    async def estimate_input(self, content: str, content_type: str = "mixed") -> int:
        """Estimate token count for input content."""
        if content_type == "code":
            return estimate_tokens(content, chars_per_token=3.5)
        elif content_type == "prose":
            return estimate_tokens(content, chars_per_token=4.0)
        else:
            return estimate_tokens(content, chars_per_token=3.75)

    async def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "unknown",
        cost_usd: float = 0.0,
    ) -> None:
        """Record token usage in the ledger."""
        if not self._ledger:
            return

        self._ledger.record(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost_usd=cost_usd,
        )

        if self._budget_limit:
            summary = self._ledger.summary()
            if summary.total_tokens > self._budget_limit:
                logger.warning(
                    "Token budget exceeded: %d/%d (limit: %d)",
                    summary.total_tokens,
                    summary.total_tokens,
                    self._budget_limit,
                )

    async def detect_waste(self, content: str) -> list[WastePattern]:
        """Detect wasteful patterns in content."""
        if not self._waste_detector or not self._waste_detection:
            return []

        self._recent_contents.append(content)
        if len(self._recent_contents) > 10:
            self._recent_contents = self._recent_contents[-10:]

        patterns = self._waste_detector.detect(content)
        if patterns:
            for p in patterns:
                logger.info("Waste detected: %s (tokens: %d)", p.pattern, p.wasted_tokens)

        return patterns

    async def check_repeated_read(self, content: str) -> bool:
        """Check if content is a repeated read of recent context."""
        if len(self._recent_contents) < 2:
            return False

        # Simple duplicate check on recent contents
        for recent in self._recent_contents[-5:]:
            if recent == content:
                return True
        return False

    async def get_summary(self) -> dict[str, Any]:
        """Get a summary of token usage."""
        if not self._ledger:
            return {"total_tokens": 0, "waste_rate": 0.0}

        summary = self._ledger.summary()
        return {
            "total_tokens": summary.total_tokens,
            "input_tokens": summary.total_input_tokens,
            "output_tokens": summary.total_output_tokens,
            "cost_usd": summary.total_cost_usd,
            "waste_rate": summary.waste_rate,
            "budget_limit": self._budget_limit,
            "budget_remaining": (
                max(0, self._budget_limit - summary.total_tokens)
                if self._budget_limit
                else None
            ),
        }