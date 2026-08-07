"""Unit tests for code_generation_service.py — Code generation service.

Tests cover:
- CodeGenerationService initialization
- execute, get_result, list_results
- run_python, run_bash
- Error paths: missing results, mock sandbox
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_execution_result() -> MagicMock:
    """Create a mock ExecutionResult."""
    mock = MagicMock()
    mock.execution_id = "exec-123"
    mock.status = "success"
    mock.output = "Hello, World!"
    mock.error = None
    mock.return_code = 0
    mock.duration_seconds = 0.5
    return mock


@pytest.fixture
def mock_code_agent_result() -> MagicMock:
    """Create a mock CodeAgentResult."""
    mock = MagicMock()
    mock.task_id = "task-456"
    mock.task_instruction = "Write a hello world program"
    mock.completion_reason = "success"
    mock.summary = "Generated Python code"
    mock.steps_executed = 3
    mock.budget = 1000
    mock.duration_seconds = 2.5
    mock.execution_history = []
    return mock


# ── Service Init Tests ─────────────────────────────────────────────────────


class TestCodeGenerationServiceInit:
    """Tests for CodeGenerationService initialization."""

    def test_service_initializes(self) -> None:
        """CodeGenerationService can be instantiated."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )
            svc = CodeGenerationService()
            assert svc is not None
            assert svc._sandbox is not None
            assert svc._agent is not None
            assert svc._results == {}


# ── Execute Tests ──────────────────────────────────────────────────────────


class TestExecute:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_execute_returns_dict(
        self, mock_code_agent_result: MagicMock
    ) -> None:
        """execute returns formatted result dict."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent") as mock_agent_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value=mock_code_agent_result)
            mock_agent_cls.return_value = mock_agent

            svc = CodeGenerationService()
            svc._agent = mock_agent

            result = await svc.execute("Write a test")
            assert result["task_id"] == "task-456"
            assert result["task_instruction"] == "Write a hello world program"
            assert result["completion_reason"] == "success"
            assert result["summary"] == "Generated Python code"
            assert result["steps_executed"] == 3
            assert result["budget"] == 1000
            assert result["duration_seconds"] == 2.5

    @pytest.mark.asyncio
    async def test_execute_with_context(
        self, mock_code_agent_result: MagicMock
    ) -> None:
        """execute passes context to agent."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent") as mock_agent_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value=mock_code_agent_result)
            mock_agent_cls.return_value = mock_agent

            svc = CodeGenerationService()
            svc._agent = mock_agent

            await svc.execute("task", context="some context")
            mock_agent.execute.assert_called_once_with(
                "task", context="some context"
            )

    @pytest.mark.asyncio
    async def test_execute_with_budget_creates_new_agent(
        self, mock_code_agent_result: MagicMock
    ) -> None:
        """execute with budget creates a new CodeAgent with the budget."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent") as mock_agent_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig") as mock_config_cls:
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value=mock_code_agent_result)
            mock_agent_cls.return_value = mock_agent

            svc = CodeGenerationService()
            svc._agent = mock_agent

            await svc.execute("task", budget=500)
            # Should have created a new agent with budget=500
            mock_config_cls.assert_called()

    @pytest.mark.asyncio
    async def test_execute_stores_result(
        self, mock_code_agent_result: MagicMock
    ) -> None:
        """execute stores the result for later retrieval."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent") as mock_agent_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value=mock_code_agent_result)
            mock_agent_cls.return_value = mock_agent

            svc = CodeGenerationService()
            svc._agent = mock_agent

            await svc.execute("task")
            assert "task-456" in svc._results
            assert svc._results["task-456"] is mock_code_agent_result


# ── Get Result Tests ───────────────────────────────────────────────────────


class TestGetResult:
    """Tests for get_result method."""

    @pytest.mark.asyncio
    async def test_get_result_existing(
        self, mock_code_agent_result: MagicMock
    ) -> None:
        """get_result returns result for existing task."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent") as mock_agent_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value=mock_code_agent_result)
            mock_agent_cls.return_value = mock_agent

            svc = CodeGenerationService()
            svc._agent = mock_agent

            await svc.execute("task")
            result = await svc.get_result("task-456")
            assert result is not None
            assert result["task_id"] == "task-456"
            assert result["completion_reason"] == "success"

    @pytest.mark.asyncio
    async def test_get_result_nonexistent(self) -> None:
        """get_result returns None for unknown task."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )
            svc = CodeGenerationService()
            result = await svc.get_result("nonexistent")
            assert result is None


# ── List Results Tests ─────────────────────────────────────────────────────


class TestListResults:
    """Tests for list_results method."""

    @pytest.mark.asyncio
    async def test_list_results_empty(self) -> None:
        """list_results returns empty list when no results."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )
            svc = CodeGenerationService()
            results = await svc.list_results()
            assert results == []

    @pytest.mark.asyncio
    async def test_list_results_with_results(
        self, mock_code_agent_result: MagicMock
    ) -> None:
        """list_results returns all stored results."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent") as mock_agent_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_agent = MagicMock()
            mock_agent.execute = AsyncMock(return_value=mock_code_agent_result)
            mock_agent_cls.return_value = mock_agent

            svc = CodeGenerationService()
            svc._agent = mock_agent

            await svc.execute("task1")
            await svc.execute("task2")

            results = await svc.list_results()
            assert len(results) == 2
            for r in results:
                assert "task_id" in r
                assert "completion_reason" in r
                assert "steps_executed" in r


# ── Run Python Tests ───────────────────────────────────────────────────────


class TestRunPython:
    """Tests for run_python method."""

    @pytest.mark.asyncio
    async def test_run_python_returns_formatted_result(
        self, mock_execution_result: MagicMock
    ) -> None:
        """run_python returns formatted execution result."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox") as mock_sandbox_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_sandbox = MagicMock()
            mock_sandbox.execute_python = AsyncMock(
                return_value=mock_execution_result
            )
            mock_sandbox_cls.return_value = mock_sandbox

            svc = CodeGenerationService()
            svc._sandbox = mock_sandbox

            result = await svc.run_python("print('hello')")
            assert result["execution_id"] == "exec-123"
            assert result["status"] == "success"
            assert result["output"] == "Hello, World!"
            assert result["return_code"] == 0
            assert result["duration_seconds"] == 0.5

    @pytest.mark.asyncio
    async def test_run_python_with_timeout(
        self, mock_execution_result: MagicMock
    ) -> None:
        """run_python passes timeout parameter to sandbox."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox") as mock_sandbox_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_sandbox = MagicMock()
            mock_sandbox.execute_python = AsyncMock(
                return_value=mock_execution_result
            )
            mock_sandbox_cls.return_value = mock_sandbox

            svc = CodeGenerationService()
            svc._sandbox = mock_sandbox

            await svc.run_python("code", timeout=10)
            mock_sandbox.execute_python.assert_called_once_with(
                "code", timeout=10
            )

    @pytest.mark.asyncio
    async def test_run_python_error_result(
        self, mock_execution_result: MagicMock
    ) -> None:
        """run_python formats error results correctly."""
        mock_execution_result.status = "error"
        mock_execution_result.output = ""
        mock_execution_result.error = "SyntaxError"
        mock_execution_result.return_code = 1

        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox") as mock_sandbox_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_sandbox = MagicMock()
            mock_sandbox.execute_python = AsyncMock(
                return_value=mock_execution_result
            )
            mock_sandbox_cls.return_value = mock_sandbox

            svc = CodeGenerationService()
            svc._sandbox = mock_sandbox

            result = await svc.run_python("invalid code")
            assert result["status"] == "error"
            assert result["error"] == "SyntaxError"
            assert result["return_code"] == 1


# ── Run Bash Tests ─────────────────────────────────────────────────────────


class TestRunBash:
    """Tests for run_bash method."""

    @pytest.mark.asyncio
    async def test_run_bash_returns_formatted_result(
        self, mock_execution_result: MagicMock
    ) -> None:
        """run_bash returns formatted execution result."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox") as mock_sandbox_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_sandbox = MagicMock()
            mock_sandbox.execute_bash = AsyncMock(
                return_value=mock_execution_result
            )
            mock_sandbox_cls.return_value = mock_sandbox

            svc = CodeGenerationService()
            svc._sandbox = mock_sandbox

            result = await svc.run_bash("echo hello")
            assert result["execution_id"] == "exec-123"
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_run_bash_with_timeout(
        self, mock_execution_result: MagicMock
    ) -> None:
        """run_bash passes timeout parameter to sandbox."""
        with patch("skpl_agent.app._service.code_generation_service.SubprocessSandbox") as mock_sandbox_cls, \
             patch("skpl_agent.app._service.code_generation_service.CodeAgent"), \
             patch("skpl_agent.app._service.code_generation_service.CodeAgentConfig"):
            from skpl_agent.app._service.code_generation_service import (
                CodeGenerationService,
            )

            mock_sandbox = MagicMock()
            mock_sandbox.execute_bash = AsyncMock(
                return_value=mock_execution_result
            )
            mock_sandbox_cls.return_value = mock_sandbox

            svc = CodeGenerationService()
            svc._sandbox = mock_sandbox

            await svc.run_bash("ls", timeout=5)
            mock_sandbox.execute_bash.assert_called_once_with(
                "ls", timeout=5
            )


# ── Format Execution Result Tests ──────────────────────────────────────────


class TestFormatExecutionResult:
    """Tests for _format_execution_result static method."""

    def test_format_execution_result(self, mock_execution_result: MagicMock) -> None:
        """_format_execution_result converts ExecutionResult to dict."""
        from skpl_agent.app._service.code_generation_service import (
            CodeGenerationService,
        )
        result = CodeGenerationService._format_execution_result(
            mock_execution_result
        )
        assert result["execution_id"] == "exec-123"
        assert result["status"] == "success"
        assert result["output"] == "Hello, World!"
        assert result["error"] is None
        assert result["return_code"] == 0
        assert result["duration_seconds"] == 0.5