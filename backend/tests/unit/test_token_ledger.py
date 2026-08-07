"""Tests for TokenLedger: token tracking, budgeting, and cost estimation."""

import pytest
from skpl_agent.context.token_ledger import (
    TokenLedger,
    TokenEntry,
    TokenLedgerSummary,
    BudgetExceededError,
)


class TestTokenRecording:
    """Basic token recording."""

    @pytest.fixture
    def ledger(self):
        return TokenLedger(session_id="test-session", agent_id="agent-001")

    def test_record_tokens(self, ledger):
        entry = ledger.record(input_tokens=500, output_tokens=200)
        assert entry.input_tokens == 500
        assert entry.output_tokens == 200
        assert entry.total_tokens == 700
        assert entry.session_id == "test-session"
        assert entry.agent_id == "agent-001"

    def test_record_with_model(self, ledger):
        entry = ledger.record(
            input_tokens=1000,
            output_tokens=500,
            model_name="gpt-4o",
            provider="openai",
        )
        assert entry.model_name == "gpt-4o"
        assert entry.provider == "openai"

    def test_record_waste(self, ledger):
        entry = ledger.record(
            input_tokens=300,
            output_tokens=100,
            is_waste=True,
            waste_reason="duplicate context",
        )
        assert entry.is_waste is True
        assert entry.waste_reason == "duplicate context"

    def test_record_text(self, ledger):
        entry = ledger.record_text(
            input_text="This is a test input message with some tokens.",
            output_text="Short output.",
        )
        assert entry.input_tokens > 0
        assert entry.output_tokens > 0

    def test_record_text_none(self, ledger):
        entry = ledger.record_text(input_text=None, output_text=None)
        assert entry.input_tokens == 0
        assert entry.output_tokens == 0


class TestTokenQueries:
    """Token usage queries and aggregations."""

    @pytest.fixture
    def ledger(self):
        l = TokenLedger(session_id="sess-1")
        l.record(input_tokens=500, output_tokens=200, model_name="gpt-4o")
        l.record(input_tokens=300, output_tokens=100, model_name="gpt-4o-mini")
        l.record(input_tokens=100, output_tokens=50, model_name="gpt-4o", is_waste=True)
        return l

    def test_total_input_tokens(self, ledger):
        assert ledger.total_input_tokens == 900

    def test_total_output_tokens(self, ledger):
        assert ledger.total_output_tokens == 350

    def test_total_tokens(self, ledger):
        assert ledger.total_tokens == 1250

    def test_total_waste_tokens(self, ledger):
        assert ledger.total_waste_tokens == 150

    def test_get_entries(self, ledger):
        entries = ledger.get_entries()
        assert len(entries) == 3

    def test_get_summary(self, ledger):
        summary = ledger.get_summary()
        assert summary.session_id == "sess-1"
        assert summary.total_tokens == 1250
        assert summary.total_waste_tokens == 150
        assert summary.entry_count == 3
        assert "gpt-4o" in summary.model_breakdown
        assert "gpt-4o-mini" in summary.model_breakdown
        assert summary.waste_rate == pytest.approx(150 / 1250, abs=0.01)


class TestTokenBudget:
    """Token budget enforcement."""

    def test_is_over_budget_false(self):
        ledger = TokenLedger(token_budget=10000)
        ledger.record(input_tokens=500, output_tokens=200)
        assert ledger.is_over_budget() is False

    def test_is_over_budget_true(self):
        ledger = TokenLedger(token_budget=500)
        ledger.record(input_tokens=400, output_tokens=200)
        assert ledger.is_over_budget() is True

    def test_no_budget(self):
        ledger = TokenLedger()
        assert ledger.is_over_budget() is False

    def test_budget_remaining(self):
        ledger = TokenLedger(token_budget=1000)
        ledger.record(input_tokens=300, output_tokens=100)
        assert ledger.budget_remaining() == 600

    def test_budget_remaining_exhausted(self):
        ledger = TokenLedger(token_budget=100)
        ledger.record(input_tokens=200, output_tokens=100)
        assert ledger.budget_remaining() == 0

    def test_budget_used_pct(self):
        ledger = TokenLedger(token_budget=1000)
        ledger.record(input_tokens=300, output_tokens=200)
        assert ledger.budget_used_pct() == 50.0

    def test_budget_used_pct_over(self):
        ledger = TokenLedger(token_budget=100)
        ledger.record(input_tokens=200, output_tokens=100)
        assert ledger.budget_used_pct() == 100.0

    def test_budget_used_pct_no_budget(self):
        ledger = TokenLedger()
        assert ledger.budget_used_pct() == 0.0


class TestTokenEntryDataclass:
    """TokenEntry dataclass."""

    def test_default_values(self):
        entry = TokenEntry(session_id="sess-1")
        assert entry.id is not None
        assert entry.input_tokens == 0
        assert entry.output_tokens == 0
        assert entry.total_tokens == 0
        assert entry.is_waste is False

    def test_total_tokens_auto(self):
        entry = TokenEntry(session_id="sess-1", input_tokens=100, output_tokens=50)
        assert entry.total_tokens == 150

    def test_total_tokens_manual(self):
        entry = TokenEntry(
            session_id="sess-1",
            input_tokens=100,
            output_tokens=50,
            total_tokens=200,
        )
        assert entry.total_tokens == 200  # manual override


class TestTokenLedgerSummaryDataclass:
    """TokenLedgerSummary dataclass."""

    def test_default_values(self):
        summary = TokenLedgerSummary(session_id="sess-1")
        assert summary.session_id == "sess-1"
        assert summary.total_tokens == 0
        assert summary.waste_rate == 0.0
        assert summary.model_breakdown == {}
        assert summary.provider_breakdown == {}


class TestBudgetExceededError:
    """BudgetExceededError."""

    def test_error_message(self):
        err = BudgetExceededError(budget=1000, used=1500)
        assert "1000" in str(err)
        assert "1500" in str(err)
        assert err.budget == 1000
        assert err.used == 1500


class TestLedgerReset:
    """Reset and clear operations."""

    def test_reset(self):
        ledger = TokenLedger()
        ledger.record(input_tokens=500, output_tokens=200)
        ledger.reset()
        assert ledger.total_tokens == 0
        assert len(ledger.get_entries()) == 0