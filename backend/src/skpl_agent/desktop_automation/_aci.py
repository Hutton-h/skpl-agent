"""Actionable Context Interface (ACI) base class.

Adapted from Agent-S gui_agents/s1/aci/ACI.py.
Provides the platform-agnostic abstraction for desktop UI automation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("skpl_agent.desktop_automation")


@dataclass
class Action:
    """A desktop automation action to execute.

    Attributes:
        type: Action type (click, type, scroll, screenshot, etc.)
        target_id: Optional element ID to target.
        x: X coordinate for click/move actions.
        y: Y coordinate for click/move actions.
        text: Text to type.
        delta_x: Horizontal scroll delta.
        delta_y: Vertical scroll delta.
    """

    type: str
    target_id: str = ""
    x: int = 0
    y: int = 0
    text: str = ""
    delta_x: int = 0
    delta_y: int = 0


@dataclass
class UIElement:
    """A UI element found during accessibility tree extraction.

    Attributes:
        id: Unique element identifier.
        name: Display name of the element.
        role: Accessibility role (button, text, etc.)
        x: Left coordinate.
        y: Top coordinate.
        width: Element width.
        height: Element height.
        children: Child elements.
    """

    id: str
    name: str
    role: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    children: list[UIElement] = field(default_factory=list)

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2


@dataclass
class ActionResult:
    """Result of executing a desktop automation action.

    Attributes:
        success: Whether the action succeeded.
        action_type: The type of action executed.
        screenshot: Optional screenshot bytes after execution.
        error: Error message if the action failed.
    """

    success: bool
    action_type: str = ""
    screenshot: bytes | None = None
    error: str | None = None


def agent_action(func):
    """Decorator to mark a method as a concrete agent action.

    The decorated method should return a string containing executable
    pyautogui code or a sentinel value (DONE / FAIL / WAIT).
    """
    func.is_agent_action = True
    return func


class ACI:
    """Base class for platform-specific Actionable Context Interfaces.

    Subclasses implement platform-specific UI tree extraction and action
    generation. Each action method is decorated with @agent_action and
    returns executable pyautogui code strings.

    Attributes:
        top_app_only: If True, only extract elements from the foreground app.
        ocr: If True, augment the accessibility tree with OCR-detected text.
        index_out_of_range_flag: Set True when find_element() falls back.
        notes: Persistent scratchpad accessible via save_to_knowledge().
        clipboard: Last clipboard value for copy/paste emulation.
        nodes: Current list of preserved UI nodes (indexed by element_id).
    """

    def __init__(self, top_app_only: bool = True, ocr: bool = False) -> None:
        self.top_app_only = top_app_only
        self.ocr = ocr
        self.index_out_of_range_flag = False
        self.notes: list[str] = []
        self.clipboard = ""
        self.nodes: list[dict[str, Any]] = []

    # ── Tree extraction (platform-specific) ──────────────────────────────

    def get_active_apps(self, obs: dict[str, Any]) -> list[str]:
        """Return a list of currently running application names."""
        raise NotImplementedError

    def get_top_app(self, obs: dict[str, Any]) -> str | None:
        """Return the name of the foreground application."""
        raise NotImplementedError

    def preserve_nodes(
        self, tree: Any, exclude_roles: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """Traverse the UI tree and return valid, visible nodes."""
        raise NotImplementedError

    def linearize_and_annotate_tree(
        self, obs: dict[str, Any], show_all_elements: bool = False
    ) -> str:
        """Build a tab-separated linearized accessibility tree string."""
        raise NotImplementedError

    def find_element(self, element_id: int) -> dict[str, Any]:
        """Look up a UI element by its index in self.nodes."""
        raise NotImplementedError