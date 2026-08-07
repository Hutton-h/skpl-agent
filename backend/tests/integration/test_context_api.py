"""Integration tests for context API, services, and middleware."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


class TestContextServiceIntegration:
    """Integration tests for ContextService."""

    @pytest.fixture
    def mock_context_manager(self):
        mock = MagicMock()
        mock.get_session_context = AsyncMock()
        mock.remove_session = MagicMock()
        mock.get_summary = MagicMock(return_value={})
        mock.search_symbols = MagicMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_scan_task_manager(self):
        mock = MagicMock()
        mock.submit = AsyncMock(return_value="task-123")
        mock.get_status = MagicMock(return_value={
            "task_id": "task-123",
            "status": "completed",
            "progress": 100,
            "progress_total": 100,
        })
        mock.get_result = MagicMock(return_value={})
        mock.get_error = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_file_watch_manager(self):
        mock = MagicMock()
        mock.start = AsyncMock(return_value=True)
        mock.stop = AsyncMock(return_value=True)
        mock.get_watched_files = MagicMock(return_value=[])
        return mock

    @pytest.mark.asyncio
    async def test_create_session(self, mock_context_manager, mock_scan_task_manager, mock_file_watch_manager):
        from skpl_agent.app._service.context_service import ContextService

        service = ContextService(
            context_manager=mock_context_manager,
            scan_task_manager=mock_scan_task_manager,
            file_watch_manager=mock_file_watch_manager,
        )

        session = await service.create_session(
            session_id="test-session",
            agent_id="agent-001",
            project_root=".",
        )

        mock_context_manager.get_session_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_scan(self, mock_context_manager, mock_scan_task_manager, mock_file_watch_manager):
        from skpl_agent.app._service.context_service import ContextService

        service = ContextService(
            context_manager=mock_context_manager,
            scan_task_manager=mock_scan_task_manager,
            file_watch_manager=mock_file_watch_manager,
        )

        task_id = await service.start_scan(root_path="/test/project", mode="full")
        assert task_id == "task-123"
        mock_scan_task_manager.submit.assert_called_once()

    def test_get_scan_status(self, mock_context_manager, mock_scan_task_manager, mock_file_watch_manager):
        from skpl_agent.app._service.context_service import ContextService

        service = ContextService(
            context_manager=mock_context_manager,
            scan_task_manager=mock_scan_task_manager,
            file_watch_manager=mock_file_watch_manager,
        )

        status = service.get_scan_status("task-123")
        assert status["status"] == "completed"
        assert status["progress"] == 100

    def test_search_symbols(self, mock_context_manager, mock_scan_task_manager, mock_file_watch_manager):
        from skpl_agent.app._service.context_service import ContextService

        mock_context_manager.search_symbols.return_value = [
            {"name": "test_func", "kind": "function", "language": "python"}
        ]

        service = ContextService(
            context_manager=mock_context_manager,
            scan_task_manager=mock_scan_task_manager,
            file_watch_manager=mock_file_watch_manager,
        )

        results = service.search_symbols(
            session_id="test-session",
            query="test_func",
            language="python",
            kind="function",
        )
        assert len(results) == 1
        assert results[0]["name"] == "test_func"

    def test_scan_task_manager_none(self, mock_context_manager):
        """Test graceful handling when scan_task_manager is None."""
        from skpl_agent.app._service.context_service import ContextService

        service = ContextService(
            context_manager=mock_context_manager,
            scan_task_manager=None,
            file_watch_manager=None,
        )

        assert service.get_scan_status("task-123") is None
        assert service.get_scan_result("task-123") is None


class TestBugLogServiceIntegration:
    """Integration tests for BugLogService."""

    def test_log_and_deduplicate(self):
        from skpl_agent.app._service.buglog_service import BugLogService
        from skpl_agent.context.buglog import BugLog

        buglog = BugLog(session_id="test-session")
        service = BugLogService(buglog)

        # Log first bug
        bug1 = service.log(
            session_id="test-session",
            error_type="SyntaxError",
            error_message="unexpected EOF",
            file_path="src/main.py",
            line_number=42,
        )
        assert bug1.error_type == "SyntaxError"

        # Log duplicate
        bug2 = service.log(
            session_id="test-session",
            error_type="SyntaxError",
            error_message="unexpected EOF",
            file_path="src/main.py",
            line_number=42,
        )
        assert bug2.duplicate_of == bug1.id

    def test_get_stats(self):
        from skpl_agent.app._service.buglog_service import BugLogService
        from skpl_agent.context.buglog import BugLog

        buglog = BugLog()
        buglog.log(error_type="SyntaxError", error_message="e1")
        buglog.log(error_type="ValueError", error_message="e2")

        service = BugLogService(buglog)
        stats = service.get_stats()
        assert stats["total"] == 2


class TestCerebrumServiceIntegration:
    """Integration tests for CerebrumService."""

    def test_remember_and_recall(self):
        from skpl_agent.app._service.cerebrum_service import CerebrumService
        from skpl_agent.context.cerebrum import Cerebrum

        brain = Cerebrum(agent_id="agent-001")
        service = CerebrumService(brain)

        mem = service.remember(
            agent_id="agent-001",
            key="pref_theme",
            value="dark",
            category="preferences",
            confidence=0.9,
        )
        assert mem.key == "pref_theme"
        assert mem.value == "dark"

        recalled = service.recall("agent-001", "pref_theme")
        assert recalled is not None
        assert recalled.value == "dark"

    def test_export_context(self):
        from skpl_agent.app._service.cerebrum_service import CerebrumService
        from skpl_agent.context.cerebrum import Cerebrum

        brain = Cerebrum()
        brain.remember("key1", "value1", category="test")

        service = CerebrumService(brain)
        context = service.export_context(max_entries=10)
        assert "key1" in context


class TestTokenLedgerServiceIntegration:
    """Integration tests for TokenLedgerService."""

    def test_record_and_check_budget(self):
        from skpl_agent.app._service.token_ledger_service import TokenLedgerService
        from skpl_agent.context.token_ledger import TokenLedger

        ledger = TokenLedger(session_id="test", token_budget=1000)
        service = TokenLedgerService(ledger)

        entry = service.record(
            session_id="test",
            input_tokens=500,
            output_tokens=200,
            model_name="gpt-4o",
        )
        assert entry.total_tokens == 700
        assert service.check_budget("test") is True

        # Exceed budget
        service.record(
            session_id="test",
            input_tokens=400,
            output_tokens=100,
        )
        assert service.check_budget("test") is False

    def test_get_summary(self):
        from skpl_agent.app._service.token_ledger_service import TokenLedgerService
        from skpl_agent.context.token_ledger import TokenLedger

        ledger = TokenLedger(session_id="test")
        ledger.record(input_tokens=100, output_tokens=50, model_name="gpt-4o")

        service = TokenLedgerService(ledger)
        summary = service.get_summary("test")
        assert summary.total_tokens == 150
        assert summary.entry_count == 1


class TestContextMiddlewareIntegration:
    """Integration tests for context middleware."""

    def test_context_middleware_creation(self):
        """Verify context middleware can be instantiated."""
        from skpl_agent.middleware._context_middleware import ContextMiddleware

        mock_context_manager = MagicMock()
        middleware = ContextMiddleware(context_manager=mock_context_manager)
        assert middleware is not None

    def test_token_middleware_creation(self):
        """Verify token middleware can be instantiated."""
        from skpl_agent.middleware._token_middleware import TokenMiddleware

        mock_token_ledger = MagicMock()
        middleware = TokenMiddleware(token_ledger=mock_token_ledger)
        assert middleware is not None


class TestEventCustomIntegration:
    """Integration tests for custom event system."""

    def test_event_enum_values(self):
        """Verify all event name enums are valid strings."""
        from skpl_agent.event._custom import SKPLContextEventName

        for name in SKPLContextEventName:
            assert isinstance(name.value, str)
            assert name.value.startswith(("context:", "desktop:"))

    def test_event_payload_schema_structure(self):
        """Verify event payload schemas have required fields."""
        from skpl_agent.event._custom import SKPL_EVENT_PAYLOADS

        for event_name, schema in SKPL_EVENT_PAYLOADS.items():
            assert "description" in schema
            assert "fields" in schema
            assert isinstance(schema["fields"], dict)

    def test_custom_event_creation(self):
        """Verify custom events can be created with the AgentScope event system."""
        from skpl_agent.event._event import CustomEvent
        from skpl_agent.event._custom import SKPLContextEventName

        event = CustomEvent(
            name=SKPLContextEventName.CONTEXT_SESSION_STARTED,
            value={
                "session_id": "test-session",
                "agent_id": "agent-001",
                "project_root": ".",
            },
        )
        assert event.name == "context:session_started"
        assert event.value["session_id"] == "test-session"
        assert event.type == "CUSTOM"