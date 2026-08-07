"""Tests for desktop executor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skpl_agent.desktop_node.executor import DesktopExecutor, RateLimitError


class TestDesktopExecutor:
    """Tests for DesktopExecutor."""

    @pytest.fixture
    def mock_aci(self):
        """Create a mock ACI."""
        aci = AsyncMock()
        aci.capture_screenshot.return_value = b"fake-screenshot"
        aci.execute_action.return_value = MagicMock(success=True)
        return aci

    @pytest.fixture
    def executor(self, mock_aci):
        """Create a DesktopExecutor with mock ACI."""
        return DesktopExecutor(
            aci=mock_aci,
            max_actions_per_second=10.0,
            max_burst=20,
        )

    @pytest.mark.asyncio
    async def test_execute_click(self, executor) -> None:
        """Executor can execute a click action."""
        result = await executor.execute("click", x=100, y=200)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_type(self, executor) -> None:
        """Executor can execute a type action."""
        result = await executor.execute("type", text="Hello")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_screenshot(self, executor) -> None:
        """Executor can capture screenshot."""
        result = await executor.execute("screenshot")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, executor) -> None:
        """Rate limiting is enforced for rapid actions."""
        executor._rate_limiter.tokens = 0  # Exhaust tokens
        with pytest.raises(RateLimitError):
            await executor.execute("click", x=100, y=100)

    @pytest.mark.asyncio
    async def test_unknown_action(self, executor) -> None:
        """Unknown action type raises ValueError."""
        with pytest.raises(ValueError):
            await executor.execute("unknown_action")


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error(self) -> None:
        """RateLimitError can be created and caught."""
        error = RateLimitError("Rate limit exceeded", retry_after=1.5)
        assert error.retry_after == 1.5
        assert "Rate limit" in str(error)