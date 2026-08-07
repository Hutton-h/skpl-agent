"""Desktop Agent — high-level agent for desktop automation tasks.

Wraps the ACI engine, screen capture, and grounding capabilities into
a single agent that can be used by the SKPL Agent framework.

Architecture:
    DesktopAgent
        ├── WindowsACI (UI tree extraction + action generation)
        ├── ScreenCapture (multi-backend screenshot)
        ├── GroundingModel (UI element detection)
        └── SecurityPolicy (safety enforcement)

Usage:
    >>> agent = DesktopAgent()
    >>> await agent.start()
    >>> tree = await agent.extract_tree()
    >>> code = agent.click(element_id=3)
    >>> await agent.execute(code)
    >>> await agent.stop()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from skpl_agent.desktop_automation import ACI, WindowsACI
from skpl_agent.desktop_node.grounding import (
    GroundingModel,
    GroundingResult,
    SimpleGrounding,
    create_grounding_model,
)
from skpl_agent.desktop_node.screen import ScreenCapture
from skpl_agent.desktop_node.security import SecurityPolicy

logger = logging.getLogger(__name__)


@dataclass
class DesktopAgentState:
    """Runtime state of a DesktopAgent."""

    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "idle"  # idle | running | paused | stopped
    current_app: str = ""
    screen_width: int = 0
    screen_height: int = 0
    action_count: int = 0
    error_count: int = 0
    last_action: str = ""
    last_error: str = ""
    start_time: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DesktopAgent:
    """High-level desktop automation agent.

    Provides a unified interface for desktop UI automation combining:
    - UI element tree extraction (via ACI)
    - Action generation (click, type, scroll, etc.)
    - Screen capture
    - UI element grounding (via OmniParser or ACI)
    - Security policy enforcement

    The agent can be used standalone or as a tool within a larger
    AgentScope pipeline.
    """

    def __init__(
        self,
        aci: Optional[ACI] = None,
        screen_capture: Optional[ScreenCapture] = None,
        grounding_model: Optional[GroundingModel] = None,
        security_policy: Optional[SecurityPolicy] = None,
        top_app_only: bool = True,
        ocr_enabled: bool = False,
    ) -> None:
        self._aci = aci or WindowsACI(
            top_app_only=top_app_only, ocr=ocr_enabled,
        )
        self._screen = screen_capture or ScreenCapture(backend="mss")
        self._grounding = grounding_model or SimpleGrounding()
        self._policy = security_policy or SecurityPolicy.default()

        self._state = DesktopAgentState()
        self._running = False

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def state(self) -> DesktopAgentState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def aci(self) -> ACI:
        return self._aci

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the desktop agent."""
        self._running = True
        self._state.status = "running"
        self._state.start_time = datetime.now(timezone.utc)

        # Get screen info
        size = self._screen.get_screen_size()
        self._state.screen_width = size[0]
        self._state.screen_height = size[1]

        logger.info(
            "DesktopAgent started: id=%s screen=%dx%d",
            self._state.agent_id, size[0], size[1],
        )

    async def stop(self) -> None:
        """Stop the desktop agent."""
        self._running = False
        self._state.status = "stopped"
        self._grounding.unload()
        logger.info(
            "DesktopAgent stopped: actions=%d errors=%d",
            self._state.action_count, self._state.error_count,
        )

    async def reset(self) -> None:
        """Reset agent state without stopping."""
        self._state = DesktopAgentState(agent_id=self._state.agent_id)
        self._aci.notes.clear()
        self._aci.clipboard = ""
        logger.info("DesktopAgent reset: %s", self._state.agent_id)

    # ── Screen ───────────────────────────────────────────────────────────

    async def screenshot(self) -> str:
        """Capture current screen as base64 JPEG.

        Returns:
            Base64-encoded JPEG image string.
        """
        return self._screen.capture_base64()

    async def screenshot_region(
        self, x: int, y: int, w: int, h: int
    ) -> str:
        """Capture a region of the screen.

        Returns:
            Base64-encoded JPEG image string.
        """
        return self._screen.capture_base64(region=(x, y, w, h))

    # ── Tree Extraction ──────────────────────────────────────────────────

    async def extract_tree(self, show_all: bool = False) -> str:
        """Extract the linearized UI accessibility tree.

        Args:
            show_all: If True, show all elements including panes/groups.

        Returns:
            Tab-separated accessibility tree text.
        """
        screenshot = await self.screenshot()
        # Convert base64 to bytes
        import base64
        img_bytes = base64.b64decode(screenshot)

        obs = {"screenshot": img_bytes}
        tree = self._aci.linearize_and_annotate_tree(
            obs, show_all_elements=show_all,
        )
        return tree

    async def get_elements(self) -> list[dict[str, Any]]:
        """Get the list of preserved UI elements from the last tree extraction.

        Returns:
            List of element dicts with position, size, title, text, role.
        """
        return self._aci.nodes

    async def get_top_app(self) -> str | None:
        """Get the name of the currently focused application."""
        return self._aci.get_top_app({})

    async def get_active_apps(self) -> list[str]:
        """Get list of currently running applications."""
        return self._aci.get_active_apps({})

    # ── Actions ──────────────────────────────────────────────────────────

    def click(
        self, element_id: int, num_clicks: int = 1, button: str = "left",
    ) -> str:
        """Generate click action code."""
        self._record_action("click")
        return self._aci.click(
            element_id=element_id, num_clicks=num_clicks, button_type=button,
        )

    def double_click(self, element_id: int) -> str:
        """Generate double-click action code."""
        self._record_action("double_click")
        return self._aci.click(element_id=element_id, num_clicks=2)

    def right_click(self, element_id: int) -> str:
        """Generate right-click action code."""
        self._record_action("right_click")
        return self._aci.click(
            element_id=element_id, button_type="right",
        )

    def type_text(
        self, text: str, element_id: int | None = None,
        overwrite: bool = False, enter: bool = False,
    ) -> str:
        """Generate type action code."""
        self._record_action("type")
        return self._aci.type(
            element_id=element_id, text=text,
            overwrite=overwrite, enter=enter,
        )

    def hotkey(self, keys: list[str]) -> str:
        """Generate hotkey action code."""
        self._record_action("hotkey")
        return self._aci.hotkey(keys=keys)

    def scroll(self, element_id: int, clicks: int) -> str:
        """Generate scroll action code."""
        self._record_action("scroll")
        return self._aci.scroll(element_id=element_id, clicks=clicks)

    def drag(self, from_id: int, to_id: int) -> str:
        """Generate drag-and-drop action code."""
        self._record_action("drag")
        return self._aci.drag_and_drop(
            drag_from_id=from_id, drop_on_id=to_id,
        )

    def open_app(self, app_name: str) -> str:
        """Generate open application action code."""
        self._policy.check_app(app_name)
        self._record_action("open_app")
        return self._aci.open(app_name)

    def switch_app(self, app_name: str) -> str:
        """Generate switch application action code."""
        self._policy.check_app(app_name)
        self._record_action("switch_app")
        return self._aci.switch_applications(app_name)

    def wait(self, seconds: float) -> str:
        """Generate wait action code."""
        self._record_action("wait")
        return self._aci.wait(time=seconds)

    async def execute(self, code: str) -> bool:
        """Execute generated action code.

        Args:
            code: Python code string to execute.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self._policy.check_code(code)
            exec(code)
            return True
        except Exception as e:
            self._state.error_count += 1
            self._state.last_error = str(e)
            logger.error("Action execution failed: %s", e)
            return False

    # ── Grounding ────────────────────────────────────────────────────────

    async def ground(
        self, instruction: str = "",
    ) -> GroundingResult:
        """Ground UI elements from the current screen.

        Args:
            instruction: Natural language instruction for grounding.

        Returns:
            GroundingResult with detected elements.
        """
        screenshot = await self.screenshot()
        return self._grounding.ground(
            image_base64=screenshot,
            instruction=instruction,
        )

    async def find_element(
        self, description: str,
    ) -> dict[str, Any] | None:
        """Find a UI element by natural language description.

        Args:
            description: What to look for (e.g., "the submit button").

        Returns:
            Element dict with bbox, label, confidence, or None.
        """
        result = await self.ground(instruction=description)
        return result.get_center_element()

    async def click_element(self, description: str) -> bool:
        """Find and click a UI element by description.

        Args:
            description: What to click (e.g., "the OK button").

        Returns:
            True if element was found and clicked.
        """
        element = await self.find_element(description)
        if element is None:
            logger.warning("Element not found: %s", description)
            return False

        bbox = element.get("bbox", [])
        if len(bbox) == 4:
            x = (bbox[0] + bbox[2]) // 2
            y = (bbox[1] + bbox[3]) // 2
            import pyautogui
            pyautogui.click(x, y)
            self._record_action("click_element")
            return True

        return False

    # ── Knowledge ────────────────────────────────────────────────────────

    def save_notes(self, *notes: str) -> None:
        """Save information to the persistent scratchpad."""
        self._aci.notes.extend(notes)

    def get_notes(self) -> list[str]:
        """Get all saved notes."""
        return list(self._aci.notes)

    # ── State ────────────────────────────────────────────────────────────

    async def get_status(self) -> dict[str, Any]:
        """Get agent status and statistics."""
        return {
            "agent_id": self._state.agent_id,
            "status": self._state.status,
            "screen_width": self._state.screen_width,
            "screen_height": self._state.screen_height,
            "action_count": self._state.action_count,
            "error_count": self._state.error_count,
            "last_action": self._state.last_action,
            "last_error": self._state.last_error,
            "uptime_seconds": (
                (datetime.now(timezone.utc) - self._state.start_time).total_seconds()
                if self._state.start_time else 0
            ),
            "aci_notes": len(self._aci.notes),
            "grounding_model": self._grounding.model_name,
        }

    def _record_action(self, action_name: str) -> None:
        """Record an action for statistics."""
        self._state.action_count += 1
        self._state.last_action = action_name