"""Unit tests for desktop_automation_service.py — Desktop automation service.

Tests cover:
- DesktopAutomationService initialization, session management
- create_session, get_session, delete_session, list_sessions
- extract_tree, dispatch_action, get_action_history
- get_available_actions, capture_screenshot
- AutomationSession, TreeElement dataclasses
- Error paths: missing sessions, invalid actions
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from skpl_agent.app._service.desktop_automation_service import (
    AutomationSession,
    DesktopAutomationService,
    TreeElement,
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_aci() -> MagicMock:
    """Create a mock ACI instance."""
    aci = MagicMock()
    aci.linearize_and_annotate_tree = MagicMock(
        return_value="id\trole\ttitle\ttext\n1\tbutton\tOK\tClick me"
    )
    # Mock agent actions
    click = MagicMock(return_value="pyautogui.click(100, 200)")
    click.is_agent_action = True
    type_action = MagicMock(return_value='pyautogui.write("hello")')
    type_action.is_agent_action = True
    aci.click = click
    aci.type = type_action
    aci._private = "should be ignored"
    return aci


@pytest.fixture
def service() -> DesktopAutomationService:
    """Create a fresh DesktopAutomationService."""
    return DesktopAutomationService()


# ── AutomationSession Tests ────────────────────────────────────────────────


class TestAutomationSession:
    """Tests for AutomationSession dataclass."""

    def test_session_has_id(self) -> None:
        """AutomationSession has a session_id."""
        session = AutomationSession(session_id="test-123")
        assert session.session_id == "test-123"

    def test_default_status_is_idle(self) -> None:
        """Default status is idle."""
        session = AutomationSession(session_id="test")
        assert session.status == "idle"

    def test_default_action_history_empty(self) -> None:
        """Default action_history is empty list."""
        session = AutomationSession(session_id="test")
        assert session.action_history == []

    def test_default_tree_text_empty(self) -> None:
        """Default tree_text is empty string."""
        session = AutomationSession(session_id="test")
        assert session.tree_text == ""

    def test_created_at_is_set(self) -> None:
        """created_at is automatically set."""
        session = AutomationSession(session_id="test")
        assert session.created_at is not None

    def test_updated_at_is_set(self) -> None:
        """updated_at is automatically set."""
        session = AutomationSession(session_id="test")
        assert session.updated_at is not None


# ── TreeElement Tests ──────────────────────────────────────────────────────


class TestTreeElement:
    """Tests for TreeElement dataclass."""

    def test_tree_element_fields(self) -> None:
        """TreeElement has correct fields."""
        elem = TreeElement(
            element_id=1,
            role="button",
            title="OK",
            text="Click me",
        )
        assert elem.element_id == 1
        assert elem.role == "button"
        assert elem.title == "OK"
        assert elem.text == "Click me"


# ── Session Management Tests ───────────────────────────────────────────────


class TestCreateSession:
    """Tests for create_session method."""

    @pytest.mark.asyncio
    async def test_create_session_returns_session(self, service: DesktopAutomationService) -> None:
        """create_session returns an AutomationSession."""
        session = await service.create_session()
        assert isinstance(session, AutomationSession)
        assert session.status == "idle"

    @pytest.mark.asyncio
    async def test_create_session_unique_ids(self, service: DesktopAutomationService) -> None:
        """Each session gets a unique ID."""
        s1 = await service.create_session()
        s2 = await service.create_session()
        assert s1.session_id != s2.session_id

    @pytest.mark.asyncio
    async def test_create_session_id_length(self, service: DesktopAutomationService) -> None:
        """Session ID is 12 hex characters."""
        session = await service.create_session()
        assert len(session.session_id) == 12

    @pytest.mark.asyncio
    async def test_create_session_added_to_sessions(self, service: DesktopAutomationService) -> None:
        """Created session is tracked in internal dict."""
        session = await service.create_session()
        retrieved = await service.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id


class TestGetSession:
    """Tests for get_session method."""

    @pytest.mark.asyncio
    async def test_get_existing_session(self, service: DesktopAutomationService) -> None:
        """get_session returns existing session."""
        session = await service.create_session()
        result = await service.get_session(session.session_id)
        assert result is session

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, service: DesktopAutomationService) -> None:
        """get_session returns None for unknown ID."""
        result = await service.get_session("nonexistent")
        assert result is None


class TestDeleteSession:
    """Tests for delete_session method."""

    @pytest.mark.asyncio
    async def test_delete_existing_session(self, service: DesktopAutomationService) -> None:
        """delete_session removes an existing session."""
        session = await service.create_session()
        result = await service.delete_session(session.session_id)
        assert result is True
        assert await service.get_session(session.session_id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, service: DesktopAutomationService) -> None:
        """delete_session returns False for unknown ID."""
        result = await service.delete_session("nonexistent")
        assert result is False


class TestListSessions:
    """Tests for list_sessions method."""

    @pytest.mark.asyncio
    async def test_list_empty(self, service: DesktopAutomationService) -> None:
        """list_sessions returns empty list when no sessions."""
        sessions = await service.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_multiple(self, service: DesktopAutomationService) -> None:
        """list_sessions returns all sessions."""
        await service.create_session()
        await service.create_session()
        await service.create_session()
        sessions = await service.list_sessions()
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_list_after_delete(self, service: DesktopAutomationService) -> None:
        """list_sessions reflects deletions."""
        s1 = await service.create_session()
        s2 = await service.create_session()
        await service.delete_session(s1.session_id)
        sessions = await service.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == s2.session_id


# ── Extract Tree Tests ─────────────────────────────────────────────────────


class TestExtractTree:
    """Tests for extract_tree method."""

    @pytest.mark.asyncio
    async def test_extract_tree_requires_session(self, service: DesktopAutomationService) -> None:
        """extract_tree raises ValueError for unknown session."""
        with pytest.raises(ValueError, match="Session not found"):
            await service.extract_tree("nonexistent")

    @pytest.mark.asyncio
    async def test_extract_tree_returns_text_and_elements(
        self, service: DesktopAutomationService
    ) -> None:
        """extract_tree returns tree_text and parsed elements."""
        session = await service.create_session()
        tree_text, elements = await service.extract_tree(session.session_id)
        assert isinstance(tree_text, str)
        assert isinstance(elements, list)

    @pytest.mark.asyncio
    async def test_extract_tree_updates_session_tree_text(
        self, service: DesktopAutomationService
    ) -> None:
        """extract_tree stores tree_text on the session."""
        session = await service.create_session()
        tree_text, _ = await service.extract_tree(session.session_id)
        updated = await service.get_session(session.session_id)
        assert updated.tree_text == tree_text

    @pytest.mark.asyncio
    async def test_extract_tree_updates_updated_at(
        self, service: DesktopAutomationService
    ) -> None:
        """extract_tree updates the session's updated_at timestamp."""
        session = await service.create_session()
        original_updated = session.updated_at
        await service.extract_tree(session.session_id)
        updated = await service.get_session(session.session_id)
        assert updated.updated_at >= original_updated


# ── Parse Tree Elements Tests ──────────────────────────────────────────────


class TestParseTreeElements:
    """Tests for _parse_tree_elements static method."""

    def test_parse_single_element(self) -> None:
        """_parse_tree_elements parses valid tree text."""
        tree_text = "id\trole\ttitle\ttext\n1\tbutton\tOK\tClick me"
        elements = DesktopAutomationService._parse_tree_elements(tree_text)
        assert len(elements) == 1
        assert elements[0].element_id == 1
        assert elements[0].role == "button"
        assert elements[0].title == "OK"
        assert elements[0].text == "Click me"

    def test_parse_multiple_elements(self) -> None:
        """_parse_tree_elements parses multiple elements."""
        tree_text = (
            "id\trole\ttitle\ttext\n"
            "1\tbutton\tOK\tClick\n"
            "2\ttextbox\tName\tEnter name\n"
            "3\tcheckbox\tAgree\tI agree"
        )
        elements = DesktopAutomationService._parse_tree_elements(tree_text)
        assert len(elements) == 3

    def test_parse_skip_header(self) -> None:
        """_parse_tree_elements skips the header row."""
        tree_text = "id\trole\ttitle\ttext\n1\tbutton\tOK\tClick"
        elements = DesktopAutomationService._parse_tree_elements(tree_text)
        assert len(elements) == 1

    def test_parse_empty_text(self) -> None:
        """_parse_tree_elements handles empty tree text."""
        elements = DesktopAutomationService._parse_tree_elements("")
        assert elements == []

    def test_parse_header_only(self) -> None:
        """_parse_tree_elements returns empty for header-only text."""
        elements = DesktopAutomationService._parse_tree_elements(
            "id\trole\ttitle\ttext"
        )
        assert elements == []

    def test_parse_invalid_lines_skipped(self) -> None:
        """_parse_tree_elements skips invalid lines."""
        tree_text = (
            "id\trole\ttitle\ttext\n"
            "invalid\tline\n"
            "1\tbutton\tOK\tClick"
        )
        elements = DesktopAutomationService._parse_tree_elements(tree_text)
        assert len(elements) == 1  # only the valid line


# ── Dispatch Action Tests ──────────────────────────────────────────────────


class TestDispatchAction:
    """Tests for dispatch_action method."""

    @pytest.mark.asyncio
    async def test_dispatch_action_requires_session(self, service: DesktopAutomationService) -> None:
        """dispatch_action raises ValueError for unknown session."""
        with pytest.raises(ValueError, match="Session not found"):
            await service.dispatch_action(
                "nonexistent", "click", {"x": 100, "y": 200}
            )

    @pytest.mark.asyncio
    async def test_dispatch_action_invalid_type(self, service: DesktopAutomationService) -> None:
        """dispatch_action raises ValueError for unknown action type."""
        session = await service.create_session()
        with pytest.raises(ValueError, match="Unknown action type"):
            await service.dispatch_action(
                session.session_id, "invalid_action", {}
            )

    @pytest.mark.asyncio
    async def test_dispatch_action_adds_to_history(self, service: DesktopAutomationService) -> None:
        """dispatch_action records the action in history."""
        session = await service.create_session()
        # Mock a valid action on the session's aci
        mock_method = MagicMock(return_value="pyautogui.click(100, 200)")
        mock_method.is_agent_action = True
        session.aci.click = mock_method

        result = await service.dispatch_action(
            session.session_id, "click", {"x": 100, "y": 200}
        )
        assert result["action_type"] == "click"
        assert result["params"] == {"x": 100, "y": 200}
        assert "code" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_dispatch_action_updates_session(self, service: DesktopAutomationService) -> None:
        """dispatch_action updates the session's updated_at."""
        session = await service.create_session()
        mock_method = MagicMock(return_value="code")
        mock_method.is_agent_action = True
        session.aci.click = mock_method

        original_updated = session.updated_at
        await service.dispatch_action(
            session.session_id, "click", {"x": 100, "y": 200}
        )
        updated = await service.get_session(session.session_id)
        assert updated.updated_at >= original_updated
        assert len(updated.action_history) == 1


# ── Get Action History Tests ───────────────────────────────────────────────


class TestGetActionHistory:
    """Tests for get_action_history method."""

    @pytest.mark.asyncio
    async def test_get_action_history_empty(self, service: DesktopAutomationService) -> None:
        """get_action_history returns empty list for new session."""
        session = await service.create_session()
        history = await service.get_action_history(session.session_id)
        assert history == []

    @pytest.mark.asyncio
    async def test_get_action_history_requires_session(self, service: DesktopAutomationService) -> None:
        """get_action_history raises ValueError for unknown session."""
        with pytest.raises(ValueError, match="Session not found"):
            await service.get_action_history("nonexistent")

    @pytest.mark.asyncio
    async def test_get_action_history_with_actions(self, service: DesktopAutomationService) -> None:
        """get_action_history returns all recorded actions."""
        session = await service.create_session()
        # Set up mock actions
        mock1 = MagicMock(return_value="code1")
        mock1.is_agent_action = True
        mock2 = MagicMock(return_value="code2")
        mock2.is_agent_action = True
        session.aci.click = mock1
        session.aci.type = mock2

        await service.dispatch_action(session.session_id, "click", {"x": 10})
        await service.dispatch_action(session.session_id, "type", {"text": "hello"})

        history = await service.get_action_history(session.session_id)
        assert len(history) == 2
        assert history[0]["action_type"] == "click"
        assert history[1]["action_type"] == "type"


# ── Get Available Actions Tests ────────────────────────────────────────────


class TestGetAvailableActions:
    """Tests for get_available_actions method."""

    @pytest.mark.asyncio
    async def test_get_available_actions_returns_list(self, service: DesktopAutomationService) -> None:
        """get_available_actions returns a list of action dicts."""
        actions = await service.get_available_actions()
        assert isinstance(actions, list)

    @pytest.mark.asyncio
    async def test_get_available_actions_have_name_and_doc(self, service: DesktopAutomationService) -> None:
        """Each action dict has name and doc keys."""
        actions = await service.get_available_actions()
        for action in actions:
            assert "name" in action
            assert "doc" in action
            assert isinstance(action["name"], str)
            assert isinstance(action["doc"], str)


# ── Capture Screenshot Tests ───────────────────────────────────────────────


class TestCaptureScreenshot:
    """Tests for capture_screenshot method."""

    @pytest.mark.asyncio
    async def test_capture_screenshot_returns_bytes(self, service: DesktopAutomationService) -> None:
        """capture_screenshot returns PNG bytes."""
        with patch("PIL.ImageGrab.grab") as mock_grab:
            mock_img = MagicMock()
            mock_img.save = MagicMock()
            mock_grab.return_value = mock_img
            result = await service.capture_screenshot()
            assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_capture_screenshot_saves_as_png(self, service: DesktopAutomationService) -> None:
        """capture_screenshot saves as PNG format."""
        with patch("PIL.ImageGrab.grab") as mock_grab:
            mock_img = MagicMock()
            mock_img.save = MagicMock()
            mock_grab.return_value = mock_img
            await service.capture_screenshot()
            mock_img.save.assert_called_once()
            call_args = mock_img.save.call_args
            assert call_args[1]["format"] == "PNG"


# ── Service Edge Cases ─────────────────────────────────────────────────────


class TestServiceEdgeCases:
    """Edge case tests for DesktopAutomationService."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, service: DesktopAutomationService) -> None:
        """Sessions are independent of each other."""
        s1 = await service.create_session()
        s2 = await service.create_session()
        # Delete s1
        await service.delete_session(s1.session_id)
        # s2 should still exist
        assert await service.get_session(s2.session_id) is not None

    @pytest.mark.asyncio
    async def test_delete_session_twice(self, service: DesktopAutomationService) -> None:
        """Deleting a session twice is safe."""
        session = await service.create_session()
        await service.delete_session(session.session_id)
        result = await service.delete_session(session.session_id)
        assert result is False