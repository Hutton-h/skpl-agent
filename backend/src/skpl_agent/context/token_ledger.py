"""
Token Ledger — Tracks token usage per session, agent, and model.

Provides a running tally of input/output tokens consumed during agent
execution, with support for waste detection, cost estimation, and
budget enforcement.

Integrates with the `skpl_token_ledgers` database table.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from skpl_agent.context.token_estimator import TokenEstimator


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class TokenEntry:
    """A single token usage record."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    agent_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    token_budget: int | None = None
    estimated_cost_usd: float | None = None
    model_name: str | None = None
    provider: str | None = None
    is_waste: bool = False
    waste_reason: str | None = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class TokenLedgerSummary:
    """Aggregated token usage summary."""

    session_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_waste_tokens: int = 0
    waste_rate: float = 0.0
    total_cost_usd: float = 0.0
    entry_count: int = 0
    model_breakdown: dict[str, int] = field(default_factory=dict)
    provider_breakdown: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


class TokenLedger:
    """In-memory token usage tracker with optional persistence.

    Usage:
        ledger = TokenLedger(session_id="sess-123", token_budget=100000)
        ledger.record(input_tokens=500, output_tokens=200, model_name="gpt-4o")
        if ledger.is_over_budget():
            raise BudgetExceededError(...)
    """

    def __init__(
        self,
        session_id: str = "",
        agent_id: str | None = None,
        token_budget: int | None = None,
        model_name: str | None = None,
        provider: str | None = None,
    ):
        self.session_id = session_id
        self.agent_id = agent_id
        self.token_budget = token_budget
        self.model_name = model_name
        self.provider = provider
        self._entries: list[TokenEntry] = []
        self._estimator = TokenEstimator()

    # -- Recording --

    def record(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model_name: str | None = None,
        provider: str | None = None,
        is_waste: bool = False,
        waste_reason: str | None = None,
    ) -> TokenEntry:
        """Record a token usage event."""
        entry = TokenEntry(
            session_id=self.session_id,
            agent_id=self.agent_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            token_budget=self.token_budget,
            model_name=model_name or self.model_name,
            provider=provider or self.provider,
            is_waste=is_waste,
            waste_reason=waste_reason,
        )

        # Estimate cost
        if entry.model_name:
            entry.estimated_cost_usd = self._estimator.estimate_cost(
                input_tokens, output_tokens, entry.model_name
            )

        self._entries.append(entry)
        return entry

    def record_text(
        self,
        input_text: str | None = None,
        output_text: str | None = None,
        model_name: str | None = None,
        provider: str | None = None,
        is_waste: bool = False,
        waste_reason: str | None = None,
    ) -> TokenEntry:
        """Record token usage from raw text (auto-estimates tokens)."""
        input_tokens = self._estimator.count(input_text) if input_text else 0
        output_tokens = self._estimator.count(output_text) if output_text else 0
        return self.record(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
            provider=provider,
            is_waste=is_waste,
            waste_reason=waste_reason,
        )

    # -- Queries --

    @property
    def total_input_tokens(self) -> int:
        return sum(e.input_tokens for e in self._entries)

    @property
    def total_output_tokens(self) -> int:
        return sum(e.output_tokens for e in self._entries)

    @property
    def total_tokens(self) -> int:
        return sum(e.total_tokens for e in self._entries)

    @property
    def total_waste_tokens(self) -> int:
        return sum(e.total_tokens for e in self._entries if e.is_waste)

    @property
    def total_cost_usd(self) -> float:
        return sum(
            e.estimated_cost_usd for e in self._entries if e.estimated_cost_usd
        )

    def is_over_budget(self) -> bool:
        """Check if total tokens exceed the budget."""
        if self.token_budget is None:
            return False
        return self.total_tokens > self.token_budget

    def budget_remaining(self) -> int | None:
        """Return remaining token budget, or None if no budget set."""
        if self.token_budget is None:
            return None
        return max(0, self.token_budget - self.total_tokens)

    def budget_used_pct(self) -> float:
        """Return percentage of budget used."""
        if self.token_budget is None or self.token_budget == 0:
            return 0.0
        return min(100.0, (self.total_tokens / self.token_budget) * 100)

    def get_summary(self) -> TokenLedgerSummary:
        """Get an aggregated summary of token usage."""
        model_breakdown: dict[str, int] = {}
        provider_breakdown: dict[str, int] = {}

        for e in self._entries:
            if e.model_name:
                model_breakdown[e.model_name] = (
                    model_breakdown.get(e.model_name, 0) + e.total_tokens
                )
            if e.provider:
                provider_breakdown[e.provider] = (
                    provider_breakdown.get(e.provider, 0) + e.total_tokens
                )

        waste_rate = (
            self.total_waste_tokens / self.total_tokens if self.total_tokens > 0 else 0.0
        )

        return TokenLedgerSummary(
            session_id=self.session_id,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            total_tokens=self.total_tokens,
            total_waste_tokens=self.total_waste_tokens,
            waste_rate=waste_rate,
            total_cost_usd=self.total_cost_usd,
            entry_count=len(self._entries),
            model_breakdown=model_breakdown,
            provider_breakdown=provider_breakdown,
        )

    def get_entries(self) -> list[TokenEntry]:
        """Get all recorded entries."""
        return list(self._entries)

    def reset(self) -> None:
        """Reset the ledger."""
        self._entries.clear()


class BudgetExceededError(Exception):
    """Raised when token usage exceeds the budget."""

    def __init__(self, budget: int, used: int):
        self.budget = budget
        self.used = used
        super().__init__(f"Token budget exceeded: {used}/{budget}")