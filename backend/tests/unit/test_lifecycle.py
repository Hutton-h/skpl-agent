"""Tests for lifecycle hooks and ContextLifecycle manager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skpl_agent.context.lifecycle import (
    AfterAgentInvokeHook,
    BeforeAgentInvokeHook,
    ContextLifecycle,
    HookContext,
    OnErrorHook,
    OnSessionEndHook,
    OnSessionStartHook,
    OnToolCallHook,
    OnToolResultHook,
    LifecycleHook,
)
from skpl_agent.context.session_context import SessionContextConfig, SessionContextManager


class TestHookContext:
    """HookContext dataclass."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        ctx = HookContext(session_id="sess-1")
        assert ctx.session_id == "sess-1"
        assert ctx.agent_id is None
        assert ctx.system_prompt is None
        assert ctx.metadata == {}

    def test_full_context(self) -> None:
        """All fields can be set."""
        ctx = HookContext(
            session_id="sess-1",
            agent_id="agent-1",
            system_prompt="You are a helpful assistant.",
            user_message="Hello",
            agent_response="Hi there!",
            tool_name="read_file",
            tool_input={"file_path": "main.py"},
            tool_output="print('hello')",
            error_type="ValueError",
            error_message="Invalid value",
            input_tokens=100,
            output_tokens=50,
            model_name="gpt-4o",
            metadata={"key": "value"},
        )
        assert ctx.agent_id == "agent-1"
        assert ctx.tool_name == "read_file"
        assert ctx.error_type == "ValueError"
        assert ctx.input_tokens == 100
        assert ctx.model_name == "gpt-4o"
        assert ctx.metadata == {"key": "value"}


class TestOnSessionStartHook:
    """OnSessionStart hook tests."""

    @pytest.mark.asyncio
    async def test_execute_with_auto_scan(self) -> None:
        """Executes anatomy scan when auto_scan_on_start is enabled."""
        config = SessionContextConfig(
            anatomy_enabled=True,
            auto_scan_on_start=True,
        )
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnSessionStartHook()
        hook_ctx = HookContext(session_id="sess-1")

        with patch.object(mgr, "scan_project", new_callable=AsyncMock) as mock_scan:
            await hook.execute_safe(mgr, hook_ctx)
            mock_scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_without_auto_scan(self) -> None:
        """Does not scan when auto_scan_on_start is disabled."""
        config = SessionContextConfig(
            anatomy_enabled=True,
            auto_scan_on_start=False,
        )
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnSessionStartHook()
        hook_ctx = HookContext(session_id="sess-1")

        with patch.object(mgr, "scan_project", new_callable=AsyncMock) as mock_scan:
            await hook.execute_safe(mgr, hook_ctx)
            mock_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self) -> None:
        """Hook handles exceptions gracefully via fallback."""
        config = SessionContextConfig(
            anatomy_enabled=True,
            auto_scan_on_start=True,
        )
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnSessionStartHook()
        hook_ctx = HookContext(session_id="sess-1")

        with patch.object(mgr, "scan_project", side_effect=RuntimeError("scan failed")):
            success = await hook.execute_safe(mgr, hook_ctx)
            assert success is False


class TestBeforeAgentInvokeHook:
    """BeforeAgentInvoke hook tests."""

    @pytest.mark.asyncio
    async def test_injects_context_into_system_prompt(self) -> None:
        """Injects context into existing system prompt."""
        config = SessionContextConfig()
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = BeforeAgentInvokeHook(max_context_tokens=10000)
        hook_ctx = HookContext(
            session_id="sess-1",
            system_prompt="You are a helpful assistant.",
        )

        with patch.object(mgr, "generate_context", return_value="## Project Anatomy\n..."):
            await hook.execute_safe(mgr, hook_ctx)
            assert hook_ctx.system_prompt is not None
            assert "You are a helpful assistant." in hook_ctx.system_prompt
            assert "## Project Anatomy" in hook_ctx.system_prompt

    @pytest.mark.asyncio
    async def test_injects_context_without_existing_prompt(self) -> None:
        """Sets system prompt when none exists."""
        config = SessionContextConfig()
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = BeforeAgentInvokeHook()
        hook_ctx = HookContext(session_id="sess-1", system_prompt=None)

        with patch.object(mgr, "generate_context", return_value="## Context\n..."):
            await hook.execute_safe(mgr, hook_ctx)
            assert hook_ctx.system_prompt == "## Context\n..."

    @pytest.mark.asyncio
    async def test_empty_context_no_injection(self) -> None:
        """Empty context does not modify system prompt."""
        config = SessionContextConfig()
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = BeforeAgentInvokeHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            system_prompt="Original prompt",
        )

        with patch.object(mgr, "generate_context", return_value=""):
            await hook.execute_safe(mgr, hook_ctx)
            assert hook_ctx.system_prompt == "Original prompt"


class TestAfterAgentInvokeHook:
    """AfterAgentInvoke hook tests."""

    @pytest.mark.asyncio
    async def test_records_token_usage(self) -> None:
        """Records token usage after agent invocation."""
        config = SessionContextConfig(token_tracking_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = AfterAgentInvokeHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            input_tokens=100,
            output_tokens=50,
            model_name="gpt-4o",
        )

        with patch.object(mgr, "record_token_usage") as mock_record:
            with patch.object(mgr, "check_budget"):
                await hook.execute_safe(mgr, hook_ctx)
                mock_record.assert_called_once_with(
                    input_tokens=100,
                    output_tokens=50,
                    model_name="gpt-4o",
                )

    @pytest.mark.asyncio
    async def test_extracts_learnings(self) -> None:
        """Extracts learnings from agent response."""
        config = SessionContextConfig(cerebrum_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = AfterAgentInvokeHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            agent_response="I learned that the project uses FastAPI. Note: async is preferred.",
        )

        with patch.object(mgr, "record_token_usage"):
            with patch.object(mgr, "check_budget"):
                with patch.object(mgr, "remember") as mock_remember:
                    await hook.execute_safe(mgr, hook_ctx)
                    assert mock_remember.call_count >= 1


class TestOnToolCallHook:
    """OnToolCall hook tests."""

    @pytest.mark.asyncio
    async def test_detects_wasteful_read(self) -> None:
        """Detects wasteful file reads."""
        config = SessionContextConfig(waste_detection_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnToolCallHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            tool_name="read_file",
            tool_input={"file_path": "main.py"},
        )

        with patch.object(mgr, "is_wasteful_read", return_value=True):
            await hook.execute_safe(mgr, hook_ctx)
            # Should not raise, just logs warning

    @pytest.mark.asyncio
    async def test_ignores_non_read_tools(self) -> None:
        """Ignores tools that are not file reads."""
        config = SessionContextConfig(waste_detection_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnToolCallHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            tool_name="grep",
            tool_input={"pattern": "test"},
        )

        with patch.object(mgr, "is_wasteful_read") as mock_waste:
            await hook.execute_safe(mgr, hook_ctx)
            mock_waste.assert_not_called()


class TestOnToolResultHook:
    """OnToolResult hook tests."""

    @pytest.mark.asyncio
    async def test_records_tool_output(self) -> None:
        """Records tool output for waste detection."""
        config = SessionContextConfig(waste_detection_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnToolResultHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            tool_name="grep",
            tool_output="found 3 matches",
        )

        with patch.object(mgr.waste_detector, "record_tool_output") as mock_record:
            await hook.execute_safe(mgr, hook_ctx)
            mock_record.assert_called_once_with("grep", "found 3 matches")

    @pytest.mark.asyncio
    async def test_tracks_file_reads(self) -> None:
        """Tracks file reads for waste detection."""
        config = SessionContextConfig(waste_detection_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnToolResultHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            tool_name="read_file",
            tool_input={"file_path": "src/main.py"},
            tool_output="print('hello')",
        )

        with patch.object(mgr, "record_file_read") as mock_record:
            await hook.execute_safe(mgr, hook_ctx)
            mock_record.assert_called_once()


class TestOnErrorHook:
    """OnError hook tests."""

    @pytest.mark.asyncio
    async def test_logs_bug(self) -> None:
        """Logs a bug on error."""
        config = SessionContextConfig(buglog_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnErrorHook()
        hook_ctx = HookContext(
            session_id="sess-1",
            error_type="ValueError",
            error_message="Invalid value",
            error_traceback="Traceback...",
            metadata={"file_path": "main.py", "line_number": 42},
        )

        with patch.object(mgr, "log_bug") as mock_log:
            with patch.object(mgr, "remember"):
                await hook.execute_safe(mgr, hook_ctx)
                mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_error_no_log(self) -> None:
        """Does not log when no error is present."""
        config = SessionContextConfig(buglog_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnErrorHook()
        hook_ctx = HookContext(session_id="sess-1")

        with patch.object(mgr, "log_bug") as mock_log:
            await hook.execute_safe(mgr, hook_ctx)
            mock_log.assert_not_called()


class TestOnSessionEndHook:
    """OnSessionEnd hook tests."""

    @pytest.mark.asyncio
    async def test_persists_summary(self) -> None:
        """Persists summary on session end."""
        config = SessionContextConfig(cerebrum_enabled=True)
        mgr = SessionContextManager(session_id="sess-1", config=config)
        hook = OnSessionEndHook()
        hook_ctx = HookContext(session_id="sess-1")

        with patch.object(mgr, "get_summary", return_value={"tokens": {"total_tokens": 100}}):
            with patch.object(mgr, "remember") as mock_remember:
                with patch.object(mgr, "shutdown"):
                    await hook.execute_safe(mgr, hook_ctx)
                    mock_remember.assert_called_once()


class TestContextLifecycle:
    """ContextLifecycle manager tests."""

    @pytest.fixture
    def lifecycle(self) -> ContextLifecycle:
        config = SessionContextConfig()
        mgr = SessionContextManager(session_id="sess-1", config=config)
        return ContextLifecycle(mgr)

    def test_register_hook(self, lifecycle: ContextLifecycle) -> None:
        """Registers a hook under its name."""
        hook = OnSessionStartHook()
        lifecycle.register(hook)
        assert "on_session_start" in lifecycle._hooks
        assert hook in lifecycle._hooks["on_session_start"]

    def test_register_multiple(self, lifecycle: ContextLifecycle) -> None:
        """Registers multiple hooks under the same name."""
        hook1 = OnSessionStartHook()
        hook2 = OnSessionStartHook()
        lifecycle.register(hook1)
        lifecycle.register(hook2)
        assert len(lifecycle._hooks["on_session_start"]) == 2

    def test_create_default_hooks(self, lifecycle: ContextLifecycle) -> None:
        """Creates all 7 default hooks."""
        hooks = lifecycle.create_default_hooks()
        assert len(hooks) == 7
        hook_names = {h.name for h in hooks}
        expected = {
            "on_session_start",
            "before_agent_invoke",
            "after_agent_invoke",
            "on_tool_call",
            "on_tool_result",
            "on_error",
            "on_session_end",
        }
        assert hook_names == expected

    def test_register_all(self, lifecycle: ContextLifecycle) -> None:
        """Registers all hooks at once."""
        hooks = lifecycle.create_default_hooks()
        lifecycle.register_all(hooks)
        assert len(lifecycle._hooks) == 7

    @pytest.mark.asyncio
    async def test_fire_empty_hooks(self, lifecycle: ContextLifecycle) -> None:
        """Firing unregistered hooks returns empty list."""
        hook_ctx = HookContext(session_id="sess-1")
        results = await lifecycle.fire("nonexistent", hook_ctx)
        assert results == []

    @pytest.mark.asyncio
    async def test_fire_registered_hook(self, lifecycle: ContextLifecycle) -> None:
        """Firing a registered hook executes it."""
        mock_hook = MagicMock(spec=LifecycleHook)
        mock_hook.name = "test_hook"
        mock_hook.execute_safe = AsyncMock(return_value=True)
        lifecycle.register(mock_hook)
        hook_ctx = HookContext(session_id="sess-1")

        results = await lifecycle.fire("test_hook", hook_ctx)
        assert results == [True]
        mock_hook.execute_safe.assert_called_once()

    @pytest.mark.asyncio
    async def test_fire_all(self, lifecycle: ContextLifecycle) -> None:
        """Fire all fires every registered hook."""
        hooks = lifecycle.create_default_hooks()
        lifecycle.register_all(hooks)
        hook_ctx = HookContext(session_id="sess-1")

        results = await lifecycle.fire_all(hook_ctx)
        assert len(results) == 7

    def test_hook_name(self) -> None:
        """Each hook has a unique name."""
        hooks = [
            OnSessionStartHook(),
            BeforeAgentInvokeHook(),
            AfterAgentInvokeHook(),
            OnToolCallHook(),
            OnToolResultHook(),
            OnErrorHook(),
            OnSessionEndHook(),
        ]
        names = {h.name for h in hooks}
        assert len(names) == 7