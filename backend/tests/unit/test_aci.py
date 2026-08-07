"""Tests for desktop ACI (Automation Control Interface)."""

from __future__ import annotations

import pytest

from skpl_agent.desktop_automation._aci import ACI, Action, ActionResult, UIElement


class TestUIElement:
    """Tests for UIElement data class."""

    def test_ui_element_creation(self) -> None:
        """UIElement can be created with basic fields."""
        element = UIElement(
            id="elem-1",
            name="Button",
            role="button",
            x=100,
            y=200,
            width=80,
            height=30,
        )
        assert element.id == "elem-1"
        assert element.name == "Button"
        assert element.role == "button"
        assert element.x == 100
        assert element.y == 200

    def test_ui_element_center(self) -> None:
        """UIElement center coordinates are correct."""
        element = UIElement(
            id="elem-1",
            name="Button",
            role="button",
            x=100,
            y=200,
            width=80,
            height=30,
        )
        assert element.center_x == 140
        assert element.center_y == 215

    def test_ui_element_defaults(self) -> None:
        """UIElement has sensible defaults."""
        element = UIElement(
            id="elem-1",
            name="Label",
            role="text",
        )
        assert element.x == 0
        assert element.y == 0
        assert element.width == 0
        assert element.height == 0
        assert element.children == []


class TestAction:
    """Tests for Action data class."""

    def test_click_action(self) -> None:
        """Click action can be created."""
        action = Action(
            type="click",
            target_id="elem-1",
            x=140,
            y=215,
        )
        assert action.type == "click"
        assert action.target_id == "elem-1"

    def test_type_action(self) -> None:
        """Type action can be created."""
        action = Action(
            type="type",
            text="Hello, World!",
        )
        assert action.type == "type"
        assert action.text == "Hello, World!"

    def test_scroll_action(self) -> None:
        """Scroll action can be created."""
        action = Action(
            type="scroll",
            delta_x=0,
            delta_y=-100,
        )
        assert action.type == "scroll"
        assert action.delta_y == -100


class TestActionResult:
    """Tests for ActionResult data class."""

    def test_success_result(self) -> None:
        """ActionResult with success status."""
        result = ActionResult(
            success=True,
            action_type="click",
            screenshot=b"fake-screenshot-data",
        )
        assert result.success is True
        assert result.action_type == "click"
        assert result.error is None

    def test_error_result(self) -> None:
        """ActionResult with error."""
        result = ActionResult(
            success=False,
            action_type="click",
            error="Element not found",
        )
        assert result.success is False
        assert result.error == "Element not found"


class TestACI:
    """Tests for ACI abstract base class."""

    def test_aci_is_abstract(self) -> None:
        """ACI cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ACI()  # type: ignore

    def test_aci_subclass(self) -> None:
        """ACI can be subclassed."""

        class TestACI(ACI):
            async def capture_screenshot(self) -> bytes:
                return b"test"

            async def extract_tree(self) -> list[UIElement]:
                return []

            async def execute_action(self, action: Action) -> ActionResult:
                return ActionResult(success=True, action_type=action.type)

            async def get_screen_size(self) -> tuple[int, int]:
                return (1920, 1080)

        aci = TestACI()
        assert aci is not None