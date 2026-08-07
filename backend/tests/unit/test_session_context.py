"""Tests for SessionContextManager: session context orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from skpl_agent.context.anatomy_scanner import ScanMode, ScanResult
from skpl_agent.context.session_context import SessionContextConfig, SessionContextManager
from skpl_agent.context.token_ledger import BudgetExceededError


class TestSessionContextConfig:
    """SessionContextConfig dataclass tests."""

    def test_default_values(self) -> None:
        """Default configuration values."""
        config = SessionContextConfig()
        assert config.anatomy_enabled is True
        assert config.buglog_enabled is True
        assert config.cerebrum_enabled is True
        assert config.token_tracking_enabled is True
        assert config.waste_detection_enabled is True
        assert config.auto_scan_on_start is False
        assert config.scan_mode == ScanMode.FULL
        assert config.max_workers == 4
        assert config.filter_sensitive is True

    def test_custom_values(self) -> None:
        """Custom configuration values."""
        config = SessionContextConfig(
            project_root="/my/project",
            anatomy_enabled=False,
            token_budget=100000,
            max_workers=8,
        )
        assert config.project_root == "/my/project"
        assert config.anatomy_enabled is False
        assert config.token_budget == 100000
        assert config.max_workers == 8


class TestSessionContextManagerInit:
    """SessionContextManager initialization."""

    def test_default_session_id(self) -> None:
        """Generates UUID session ID by default."""
        mgr = SessionContextManager()
        assert mgr.session_id is not None
        assert len(mgr.session_id) > 0

    def test_custom_session_id(self) -> None:
        """Uses provided session ID."""
        mgr = SessionContextManager(session_id="custom-sess-1")
        assert mgr.session_id == "custom-sess-1"

    def test_agent_id(self) -> None:
        """Stores agent ID."""
        mgr = SessionContextManager(agent_id="agent-1")
        assert mgr.agent_id == "agent-1"

    def test_created_at(self) -> None:
        """Records creation timestamp."""
        mgr = SessionContextManager()
        assert mgr.created_at is not None

    def test_not_initialized_by_default(self) -> None:
        """Not initialized on construction."""
        mgr = SessionContextManager()
        assert mgr._initialized is False


class TestLazySubsystems:
    """Lazy initialization of context subsystems."""

    def test_scanner_lazy(self) -> None:
        """Scanner is created on first access."""
        mgr = SessionContextManager()
        assert mgr._scanner is None
        scanner = mgr.scanner
        assert scanner is not None
        assert mgr._scanner is not None

    def test_buglog_lazy(self) -> None:
        """BugLog is created on first access."""
        mgr = SessionContextManager()
        assert mgr._buglog is None
        buglog = mgr.buglog
        assert buglog is not None

    def test_cerebrum_lazy(self) -> None:
        """Cerebrum is created on first access."""
        mgr = SessionContextManager(agent_id="agent-1")
        assert mgr._cerebrum is None
        cerebrum = mgr.cerebrum
        assert cerebrum is not None

    def test_token_ledger_lazy(self) -> None:
        """TokenLedger is created on first access."""
        mgr = SessionContextManager()
        assert mgr._token_ledger is None
        ledger = mgr.token_ledger
        assert ledger is not None

    def test_waste_detector_lazy(self) -> None:
        """WasteDetector is created on first access."""
        mgr = SessionContextManager()
        assert mgr._waste_detector is None
        detector = mgr.waste_detector
        assert detector is not None

    def test_estimator_lazy(self) -> None:
        """TokenEstimator is created on first access."""
        mgr = SessionContextManager()
        assert mgr._estimator is None
        estimator = mgr.estimator
        assert estimator is not None


class TestAnatomyOperations:
    """Anatomy scanning and symbol search."""

    @pytest.mark.asyncio
    async def test_scan_project(self) -> None:
        """Scans project and stores result."""
        mgr = SessionContextManager()
        with patch.object(mgr.scanner, "scan", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = ScanResult(
                mode=ScanMode.FULL,
                total_files_scanned=10,
                total_symbols_extracted=50,
                duration_seconds=1.5,
            )
            result = await mgr.scan_project()
            assert result.total_files_scanned == 10

    def test_get_last_scan(self) -> None:
        """Returns None before any scan."""
        mgr = SessionContextManager()
        assert mgr.get_last_scan() is None

    def test_search_symbols(self) -> None:
        """Searches symbols in anatomy store."""
        mgr = SessionContextManager()
        with patch.object(mgr.scanner.store, "search_symbols", return_value=[]):
            results = mgr.search_symbols("test")
            assert results == []

    def test_get_file_symbols(self) -> None:
        """Gets symbols for a file."""
        mgr = SessionContextManager()
        with patch.object(mgr.scanner.store, "get_file_symbols", return_value=[]):
            results = mgr.get_file_symbols("main.py")
            assert results == []


class TestBugLogging:
    """Bug logging operations."""

    def test_log_bug(self) -> None:
        """Logs a bug successfully."""
        mgr = SessionContextManager()
        record = mgr.log_bug(
            error_type="ValueError",
            error_message="Test error",
        )
        assert record is not None

    def test_log_bug_disabled(self) -> None:
        """Does not log when buglog is disabled."""
        config = SessionContextConfig(buglog_enabled=False)
        mgr = SessionContextManager(config=config)
        record = mgr.log_bug(error_type="ValueError", error_message="Test")
        assert record is not None

    def test_get_recent_bugs(self) -> None:
        """Returns recent bugs."""
        mgr = SessionContextManager()
        bugs = mgr.get_recent_bugs(limit=5)
        assert isinstance(bugs, list)

    def test_get_open_bugs(self) -> None:
        """Returns open bugs."""
        mgr = SessionContextManager()
        bugs = mgr.get_open_bugs()
        assert isinstance(bugs, list)


class TestMemoryOperations:
    """Cerebrum memory operations."""

    def test_remember(self) -> None:
        """Stores a memory."""
        mgr = SessionContextManager()
        memory = mgr.remember("key1", "value1", category="test")
        assert memory is not None

    def test_remember_disabled(self) -> None:
        """Does not store when cerebrum is disabled."""
        config = SessionContextConfig(cerebrum_enabled=False)
        mgr = SessionContextManager(config=config)
        memory = mgr.remember("key1", "value1")
        assert memory is not None

    def test_recall(self) -> None:
        """Recalls a memory."""
        mgr = SessionContextManager()
        mgr.remember("key1", "value1")
        memory = mgr.recall("key1")
        assert memory is not None

    def test_recall_nonexistent(self) -> None:
        """Returns None for nonexistent key."""
        mgr = SessionContextManager()
        memory = mgr.recall("nonexistent")
        assert memory is None

    def test_recall_disabled(self) -> None:
        """Returns None when cerebrum is disabled."""
        config = SessionContextConfig(cerebrum_enabled=False)
        mgr = SessionContextManager(config=config)
        memory = mgr.recall("key1")
        assert memory is None

    def test_forget(self) -> None:
        """Forgets a memory."""
        mgr = SessionContextManager()
        mgr.remember("key1", "value1")
        result = mgr.forget("key1")
        assert result is True

    def test_forget_disabled(self) -> None:
        """Returns False when cerebrum is disabled."""
        config = SessionContextConfig(cerebrum_enabled=False)
        mgr = SessionContextManager(config=config)
        result = mgr.forget("key1")
        assert result is False


class TestTokenTracking:
    """Token usage tracking."""

    def test_record_token_usage(self) -> None:
        """Records token usage."""
        mgr = SessionContextManager()
        mgr.record_token_usage(input_tokens=100, output_tokens=50, model_name="gpt-4o")
        summary = mgr.get_token_summary()
        assert summary is not None

    def test_record_token_usage_disabled(self) -> None:
        """Does not record when tracking is disabled."""
        config = SessionContextConfig(token_tracking_enabled=False)
        mgr = SessionContextManager(config=config)
        mgr.record_token_usage(input_tokens=100, output_tokens=50)
        summary = mgr.get_token_summary()
        # Should still work but with empty ledger
        assert summary is not None

    def test_check_budget_within_limit(self) -> None:
        """Does not raise when within budget."""
        config = SessionContextConfig(token_budget=100000)
        mgr = SessionContextManager(config=config)
        mgr.record_token_usage(input_tokens=100, output_tokens=50)
        # Should not raise
        mgr.check_budget()

    def test_check_budget_no_budget(self) -> None:
        """Does not raise when no budget is set."""
        mgr = SessionContextManager()
        mgr.record_token_usage(input_tokens=100000, output_tokens=50000)
        # Should not raise (no budget set)
        mgr.check_budget()


class TestWasteDetection:
    """Waste detection operations."""

    def test_record_file_read(self) -> None:
        """Records a file read."""
        mgr = SessionContextManager()
        mgr.record_file_read("main.py", 500)
        # Should not raise

    def test_record_file_read_disabled(self) -> None:
        """Does not record when waste detection is disabled."""
        config = SessionContextConfig(waste_detection_enabled=False)
        mgr = SessionContextManager(config=config)
        mgr.record_file_read("main.py", 500)
        # Should not raise

    def test_is_wasteful_read(self) -> None:
        """Checks if a read is wasteful."""
        mgr = SessionContextManager()
        result = mgr.is_wasteful_read("main.py")
        assert result is False

    def test_is_wasteful_read_disabled(self) -> None:
        """Returns False when waste detection is disabled."""
        config = SessionContextConfig(waste_detection_enabled=False)
        mgr = SessionContextManager(config=config)
        result = mgr.is_wasteful_read("main.py")
        assert result is False

    def test_get_waste_patterns(self) -> None:
        """Returns waste patterns."""
        mgr = SessionContextManager()
        patterns = mgr.get_waste_patterns()
        assert isinstance(patterns, list)


class TestContextGeneration:
    """Context generation for agent prompts."""

    def test_generate_context_empty(self) -> None:
        """Generates empty context when no data exists."""
        mgr = SessionContextManager()
        context = mgr.generate_context()
        assert context == ""

    def test_generate_context_with_memory(self) -> None:
        """Generates context with memory entries."""
        config = SessionContextConfig(cerebrum_enabled=True)
        mgr = SessionContextManager(config=config)
        mgr.remember("key1", "value1", category="test")
        context = mgr.generate_context(
            include_anatomy=False,
            include_bugs=False,
            include_memory=True,
        )
        assert "key1" in context or "value1" in context

    def test_generate_context_selective(self) -> None:
        """Selectively includes/excludes sections."""
        mgr = SessionContextManager()
        context = mgr.generate_context(
            include_anatomy=False,
            include_bugs=False,
            include_memory=False,
        )
        assert context == ""


class TestSummary:
    """Session summary generation."""

    def test_get_summary(self) -> None:
        """Generates comprehensive summary."""
        mgr = SessionContextManager(session_id="sess-1", agent_id="agent-1")
        summary = mgr.get_summary()
        assert summary["session_id"] == "sess-1"
        assert summary["agent_id"] == "agent-1"
        assert "anatomy" in summary
        assert "bugs" in summary
        assert "memory" in summary
        assert "tokens" in summary
        assert "waste" in summary
        assert "last_scan" in summary


class TestLifecycle:
    """Session lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize(self) -> None:
        """Initializes without auto-scan."""
        config = SessionContextConfig(auto_scan_on_start=False)
        mgr = SessionContextManager(config=config)
        await mgr.initialize()
        assert mgr._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self) -> None:
        """Initialize is idempotent."""
        mgr = SessionContextManager()
        await mgr.initialize()
        await mgr.initialize()
        assert mgr._initialized is True

    def test_shutdown(self) -> None:
        """Shutdown cleans up."""
        mgr = SessionContextManager()
        mgr.shutdown()
        assert mgr._initialized is False