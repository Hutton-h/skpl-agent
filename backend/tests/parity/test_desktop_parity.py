"""Parity tests for desktop automation modules.

Ensures the Python implementations match the original Agent-S TypeScript
behavior for coordinate mapping, action execution, and UI tree parsing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skpl_agent.desktop_node.grounding_coordinate import CoordinateMapper


class TestCoordinateParity:
    """Verify coordinate mapping matches Agent-S behavior."""

    @pytest.mark.parametrize(
        "src_w,src_h,tgt_w,tgt_h,src_x,src_y,expected_x,expected_y",
        [
            # Same size — no change
            (1920, 1080, 1920, 1080, 100, 200, 100, 200),
            # Half size
            (1920, 1080, 960, 540, 100, 200, 50, 100),
            # Double size
            (960, 540, 1920, 1080, 50, 100, 100, 200),
            # Origin stays origin
            (800, 600, 1024, 768, 0, 0, 0, 0),
            # Edge cases
            (1920, 1080, 800, 600, 1920, 1080, 800, 600),
            # Non-uniform scaling
            (1920, 1080, 1024, 768, 960, 540, 512, 384),
        ],
    )
    def test_coordinate_mapping(
        self, src_w, src_h, tgt_w, tgt_h, src_x, src_y, expected_x, expected_y,
    ) -> None:
        mapper = CoordinateMapper(
            source_width=src_w, source_height=src_h,
            target_width=tgt_w, target_height=tgt_h,
        )
        x, y = mapper.map(src_x, src_y)
        assert x == expected_x, f"Expected x={expected_x}, got x={x}"
        assert y == expected_y, f"Expected y={expected_y}, got y={y}"


class TestActionSerialization:
    """Verify action serialization matches Agent-S protocol."""

    def test_click_serialization(self) -> None:
        from skpl_agent.desktop_automation._aci import Action
        action = Action(type="click", x=100, y=200, target_id="elem-1")
        serialized = json.dumps(action.__dict__, default=str)
        assert "click" in serialized
        assert "100" in serialized

    def test_type_serialization(self) -> None:
        from skpl_agent.desktop_automation._aci import Action
        action = Action(type="type", text="Hello World")
        serialized = json.dumps(action.__dict__, default=str)
        assert "type" in serialized
        assert "Hello World" in serialized

    def test_scroll_serialization(self) -> None:
        from skpl_agent.desktop_automation._aci import Action
        action = Action(type="scroll", delta_x=0, delta_y=-100)
        serialized = json.dumps(action.__dict__, default=str)
        assert "scroll" in serialized


class TestUIElementParity:
    """Verify UI element handling matches Agent-S."""

    def test_element_tree_structure(self) -> None:
        from skpl_agent.desktop_automation._aci import UIElement

        child = UIElement(id="2", name="Button", role="button")
        parent = UIElement(
            id="1",
            name="Window",
            role="window",
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].name == "Button"

    def test_element_center(self) -> None:
        from skpl_agent.desktop_automation._aci import UIElement

        element = UIElement(
            id="1", name="Button", role="button",
            x=100, y=200, width=80, height=30,
        )
        assert element.center_x == 140
        assert element.center_y == 215

    def test_deeply_nested_tree(self) -> None:
        from skpl_agent.desktop_automation._aci import UIElement

        leaf = UIElement(id="4", name="Text", role="text")
        mid = UIElement(id="3", name="Panel", role="panel", children=[leaf])
        top = UIElement(id="2", name="Group", role="group", children=[mid])
        root = UIElement(id="1", name="Window", role="window", children=[top])

        # Verify depth
        assert len(root.children) == 1
        assert len(root.children[0].children) == 1
        assert len(root.children[0].children[0].children) == 1
        assert root.children[0].children[0].children[0].name == "Text"