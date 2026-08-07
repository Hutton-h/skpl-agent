"""Tests for context types (Pydantic models)."""

from __future__ import annotations

from datetime import datetime

import pytest

from skpl_agent.context.types import (
    BugDeduplicationResult,
    BugRecord,
    BugSeverity,
    BugStatus,
    FileHash,
    FileType,
    HookContext,
    HookResult,
    LifecyclePhase,
    ScanMode,
    ScanOptions,
    ScanResult,
    SensitivePattern,
    SensitiveScanResult,
    SessionContext,
    SessionContextConfig,
    Symbol,
    SymbolKind,
    TokenBudget,
    TokenCategory,
    TokenEntry,
    TokenLedgerSummary,
)


class TestSymbol:
    """Tests for Symbol Pydantic model."""

    def test_symbol_creation(self) -> None:
        """Symbol can be created with minimal fields."""
        sym = Symbol(name="my_function", kind=SymbolKind.FUNCTION)
        assert sym.name == "my_function"
        assert sym.kind == SymbolKind.FUNCTION
        assert sym.full_name == "my_function"

    def test_symbol_full_name_with_parent(self) -> None:
        """Symbol full_name includes parent when present."""
        sym = Symbol(
            name="method",
            kind=SymbolKind.METHOD,
            parent="MyClass",
        )
        assert sym.full_name == "MyClass.method"

    def test_symbol_defaults(self) -> None:
        """Symbol has sensible defaults."""
        sym = Symbol(name="x", kind=SymbolKind.VARIABLE)
        assert sym.line == 0
        assert sym.language == FileType.UNKNOWN
        assert sym.decorators == []
        assert sym.children == []


class TestScanOptions:
    """Tests for ScanOptions model."""

    def test_defaults(self) -> None:
        """ScanOptions has sensible defaults."""
        opts = ScanOptions()
        assert opts.mode == ScanMode.FULL
        assert opts.max_depth == 10
        assert opts.max_files == 500
        assert opts.include_docstrings is True
        assert opts.parallel is True

    def test_validation_bounds(self) -> None:
        """ScanOptions validates numeric bounds."""
        with pytest.raises(Exception):
            ScanOptions(max_depth=0)  # Below minimum
        with pytest.raises(Exception):
            ScanOptions(max_files=10000)  # Above maximum


class TestScanResult:
    """Tests for ScanResult model."""

    def test_success_rate_no_files(self) -> None:
        """Success rate is 0 when no files scanned."""
        result = ScanResult(project_root="/test", scan_mode=ScanMode.FULL)
        assert result.success_rate == 0.0

    def test_success_rate_perfect(self) -> None:
        """Success rate is 1.0 when all files scanned."""
        result = ScanResult(
            project_root="/test",
            scan_mode=ScanMode.FULL,
            total_files=10,
            scanned_files=10,
        )
        assert result.success_rate == 1.0

    def test_success_rate_partial(self) -> None:
        """Success rate reflects partial scan."""
        result = ScanResult(
            project_root="/test",
            scan_mode=ScanMode.FULL,
            total_files=10,
            scanned_files=7,
        )
        assert result.success_rate == 0.7


class TestTokenModels:
    """Tests for token-related models."""

    def test_token_entry_creation(self) -> None:
        """TokenEntry can be created with required fields."""
        entry = TokenEntry(
            id="entry-1",
            session_id="session-1",
            input_tokens=100,
            output_tokens=50,
        )
        assert entry.total_tokens == 0  # Default, not auto-computed

    def test_token_ledger_summary(self) -> None:
        """TokenLedgerSummary has sensible defaults."""
        summary = TokenLedgerSummary(session_id="session-1")
        assert summary.total_tokens == 0
        assert summary.waste_rate == 0.0

    def test_token_budget_validation(self) -> None:
        """TokenBudget validates threshold range."""
        budget = TokenBudget(max_tokens=10000, warning_threshold=0.8)
        assert budget.warning_threshold == 0.8

        with pytest.raises(Exception):
            TokenBudget(max_tokens=10000, warning_threshold=1.5)


class TestBugModels:
    """Tests for bug-related models."""

    def test_bug_record_creation(self) -> None:
        """BugRecord can be created."""
        bug = BugRecord(
            id="bug-1",
            session_id="session-1",
            error_type="ValueError",
            error_message="Something went wrong",
            severity=BugSeverity.HIGH,
        )
        assert bug.status == BugStatus.NEW
        assert bug.occurrence_count == 1
        assert bug.tags == []

    def test_bug_deduplication(self) -> None:
        """BugDeduplicationResult works."""
        result = BugDeduplicationResult(
            is_duplicate=True,
            similarity=0.95,
            matched_bug_id="bug-1",
        )
        assert result.is_duplicate is True
        assert result.similarity == 0.95


class TestLifecycleModels:
    """Tests for lifecycle-related models."""

    def test_hook_context(self) -> None:
        """HookContext can be created."""
        ctx = HookContext(
            session_id="session-1",
            phase=LifecyclePhase.ON_SESSION_START,
        )
        assert ctx.agent_id is None
        assert ctx.metadata == {}

    def test_hook_result(self) -> None:
        """HookResult can be created."""
        result = HookResult(
            hook_name="test_hook",
            phase=LifecyclePhase.BEFORE_AGENT_INVOKE,
            success=True,
        )
        assert result.success is True
        assert result.warnings == []


class TestSessionModels:
    """Tests for session-related models."""

    def test_session_context_config(self) -> None:
        """SessionContextConfig has sensible defaults."""
        config = SessionContextConfig()
        assert config.max_context_tokens == 32000
        assert config.anatomy_injection is True
        assert config.token_tracking is True

    def test_session_context(self) -> None:
        """SessionContext can be created."""
        ctx = SessionContext(
            session_id="session-1",
            project_root="/test/project",
        )
        assert ctx.recent_bugs == []
        assert ctx.token_summary is None


class TestSensitiveModels:
    """Tests for sensitive content models."""

    def test_sensitive_pattern(self) -> None:
        """SensitivePattern works."""
        pattern = SensitivePattern(
            pattern_name="API_KEY",
            category="api_key",
            matched_text="sk-1234567890",
            severity=BugSeverity.CRITICAL,
        )
        assert pattern.redacted is False

    def test_sensitive_scan_result(self) -> None:
        """SensitiveScanResult works."""
        scan = SensitiveScanResult(
            has_sensitive=True,
            pattern_count=2,
        )
        assert scan.has_sensitive is True
        assert scan.scan_duration_ms == 0.0


class TestFileHash:
    """Tests for FileHash model."""

    def test_file_hash_creation(self) -> None:
        """FileHash can be created."""
        fh = FileHash(
            path="src/main.py",
            sha256="abc123",
            size=1024,
        )
        assert fh.path == "src/main.py"
        assert fh.sha256 == "abc123"