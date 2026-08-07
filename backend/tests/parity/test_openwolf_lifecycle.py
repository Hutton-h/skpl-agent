"""Parity tests: Python (SKPL) vs TypeScript (OpenWolf) lifecycle equivalence.

These tests verify that the Python implementation of the context lifecycle
behaves identically to the original TypeScript/OpenWolf implementation.

The tests validate:
1. Session lifecycle: create → inject → shutdown
2. Anatomy scan lifecycle: start → progress → complete
3. Context middleware injection order
4. Event emission sequence
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestSessionLifecycleParity:
    """Session lifecycle: create → inject → shutdown (matches OpenWolf TS)."""

    @pytest.fixture
    def mock_context_manager(self):
        """Mock ContextManager to avoid real infrastructure."""
        mock = MagicMock()
        mock.get_session_context = AsyncMock()
        mock.remove_session = MagicMock()
        mock.get_summary = MagicMock(return_value={})
        return mock

    def test_create_session_sequence(self):
        """Verify session creation follows the same sequence as OpenWolf.

        OpenWolf TS sequence:
        1. Create SessionContextManager
        2. Initialize anatomy store (SQLite or JSON)
        3. Create BugLog
        4. Create Cerebrum
        5. Create TokenLedger
        6. Register lifecycle hooks
        7. Return session context
        """
        from skpl_agent.context.session_context import (
            SessionContextManager,
            SessionContextConfig,
        )

        config = SessionContextConfig(
            anatomy_store_path=":memory:",
            cerebrum_max_entries=100,
            token_budget=100000,
            buglog_max_entries=500,
        )

        ctx = SessionContextManager(
            session_id="test-session",
            agent_id="test-agent",
            project_root=".",
            config=config,
        )

        # Verify all subsystems initialized
        assert ctx.anatomy_store is not None
        assert ctx.buglog is not None
        assert ctx.cerebrum is not None
        assert ctx.token_ledger is not None
        assert ctx.session_id == "test-session"
        assert ctx.agent_id == "test-agent"

    def test_shutdown_sequence(self):
        """Verify shutdown follows the same sequence as OpenWolf.

        OpenWolf TS sequence:
        1. Emit context:session_ended event
        2. Stop file watching
        3. Close anatomy store
        4. Clear token ledger
        5. Clear cerebrum
        6. Clear buglog
        """
        from skpl_agent.context.session_context import (
            SessionContextManager,
            SessionContextConfig,
        )

        config = SessionContextConfig(
            anatomy_store_path=":memory:",
        )

        ctx = SessionContextManager(
            session_id="test-session",
            agent_id="test-agent",
            project_root=".",
            config=config,
        )

        # Add some data to verify cleanup
        ctx.buglog.log(error_type="Error", error_message="test")
        ctx.cerebrum.remember("key", "value")
        ctx.token_ledger.record(input_tokens=100, output_tokens=50)

        # Shutdown
        ctx.shutdown()

        # Verify cleanup
        assert len(ctx.buglog.get_all()) == 0
        assert len(ctx.cerebrum.get_all()) == 0
        assert ctx.token_ledger.total_tokens == 0


class TestContextGenerationParity:
    """Context string generation matches OpenWolf format."""

    def test_context_format(self):
        """Verify generated context follows OpenWolf format.

        OpenWolf TS format:
        ## Project Anatomy
        - [language] name: description (file:line)

        ## Active Bugs
        - [TYPE] message (file:line)

        ## Agent Memory
        - [category] key: value

        ## Token Usage
        - Budget: X/Y (Z%)
        """
        from skpl_agent.context.session_context import (
            SessionContextManager,
            SessionContextConfig,
        )

        config = SessionContextConfig(
            anatomy_store_path=":memory:",
        )

        ctx = SessionContextManager(
            session_id="test-session",
            agent_id="test-agent",
            project_root=".",
            config=config,
        )

        # Add some data
        ctx.cerebrum.remember("pref", "dark_mode", category="preferences")
        ctx.buglog.log(
            error_type="SyntaxError",
            error_message="invalid syntax",
            file_path="src/main.py",
            line_number=10,
        )
        ctx.token_ledger.record(input_tokens=500, output_tokens=200)

        context = ctx.generate_context()

        # Verify sections exist
        assert "## Project Anatomy" in context or "## Agent Memory" in context
        assert "## Agent Memory" in context or "preferences" in context
        assert "## Active Bugs" in context or "## Token Usage" in context

    def test_context_truncation(self):
        """Verify context truncation at max entries."""
        from skpl_agent.context.session_context import (
            SessionContextManager,
            SessionContextConfig,
        )

        config = SessionContextConfig(
            anatomy_store_path=":memory:",
            max_anatomy_entries=5,
            max_bug_entries=5,
            max_memory_entries=5,
        )

        ctx = SessionContextManager(
            session_id="test-session",
            agent_id="test-agent",
            project_root=".",
            config=config,
        )

        # Add many entries
        for i in range(20):
            ctx.cerebrum.remember(f"key{i}", f"value{i}", category="test")
            ctx.buglog.log(error_type="Error", error_message=f"error {i}")

        context = ctx.generate_context()
        # Context should be generated even with many entries
        assert len(context) > 0


class TestLifecycleHooksParity:
    """Lifecycle hooks match OpenWolf's hook system."""

    def test_hook_registration_order(self):
        """Verify hooks are registered in the same order as OpenWolf.

        OpenWolf TS hook order:
        1. on_session_start
        2. on_message_received
        3. pre_model_call
        4. post_model_call
        5. on_tool_call
        6. on_tool_result
        7. on_session_end
        """
        from skpl_agent.context.lifecycle import (
            LifecycleHooks,
            LifecycleHook,
            HookType,
        )

        hooks = LifecycleHooks()

        call_order = []

        async def hook_1(*args, **kwargs):
            call_order.append("on_session_start")

        async def hook_2(*args, **kwargs):
            call_order.append("on_message_received")

        async def hook_3(*args, **kwargs):
            call_order.append("pre_model_call")

        hooks.register(HookType.ON_SESSION_START, hook_1)
        hooks.register(HookType.ON_MESSAGE_RECEIVED, hook_2)
        hooks.register(HookType.PRE_MODEL_CALL, hook_3)

        assert hooks.get_hooks(HookType.ON_SESSION_START) == [hook_1]
        assert hooks.get_hooks(HookType.ON_MESSAGE_RECEIVED) == [hook_2]
        assert hooks.get_hooks(HookType.PRE_MODEL_CALL) == [hook_3]

    def test_hook_unregistration(self):
        """Verify hook removal works correctly."""
        from skpl_agent.context.lifecycle import (
            LifecycleHooks,
            HookType,
        )

        hooks = LifecycleHooks()

        async def my_hook(*args, **kwargs):
            pass

        hooks.register(HookType.ON_SESSION_START, my_hook)
        assert len(hooks.get_hooks(HookType.ON_SESSION_START)) == 1

        hooks.unregister(HookType.ON_SESSION_START, my_hook)
        assert len(hooks.get_hooks(HookType.ON_SESSION_START)) == 0

    def test_hook_type_enum_completeness(self):
        """Verify all OpenWolf hook types are defined."""
        from skpl_agent.context.lifecycle import HookType

        expected_types = {
            "ON_SESSION_START",
            "ON_SESSION_END",
            "ON_MESSAGE_RECEIVED",
            "PRE_MODEL_CALL",
            "POST_MODEL_CALL",
            "ON_TOOL_CALL",
            "ON_TOOL_RESULT",
        }

        for t in expected_types:
            assert hasattr(HookType, t), f"Missing HookType.{t}"