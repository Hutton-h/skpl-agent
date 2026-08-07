"""Desktop automation service layer.

Bridges the ACI engine with the REST API — manages automation sessions,
dispatches actions, and captures screenshots.
"""

from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from PIL import ImageGrab

logger = logging.getLogger(__name__)


def _create_aci():
    """Lazy-create a WindowsACI instance (platform-specific)."""
    from skpl_agent.desktop_automation import WindowsACI
    return WindowsACI()


@dataclass
class AutomationSession:
    """A single desktop automation session."""

    session_id: str
    status: str = "idle"  # idle | running | completed | failed
    aci: Any = field(default_factory=_create_aci)
    tree_text: str = ""
    screenshot: bytes | None = None
    action_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TreeElement:
    """Parsed element from the linearized accessibility tree."""

    element_id: int
    role: str
    title: str
    text: str


class DesktopAutomationService:
    """Service for desktop automation operations.

    Manages ACI sessions, captures screenshots, extracts UI trees,
    and dispatches pyautogui action code.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, AutomationSession] = {}

    # ── Session management ───────────────────────────────────────────────

    async def create_session(self) -> AutomationSession:
        """Create a new automation session with a fresh ACI instance."""
        session_id = uuid.uuid4().hex[:12]
        session = AutomationSession(session_id=session_id)
        self._sessions[session_id] = session
        logger.info("Automation session created: %s", session_id)
        return session

    async def get_session(self, session_id: str) -> AutomationSession | None:
        """Get an existing session by ID."""
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and release resources."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Automation session deleted: %s", session_id)
            return True
        return False

    async def list_sessions(self) -> list[AutomationSession]:
        """List all active sessions."""
        return list(self._sessions.values())

    # ── Screenshot ───────────────────────────────────────────────────────

    async def capture_screenshot(self) -> bytes:
        """Capture the current screen as PNG bytes."""
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # ── Tree extraction ───────────────────────────────────────────────────

    async def extract_tree(
        self, session_id: str, show_all: bool = False
    ) -> tuple[str, list[TreeElement]]:
        """Extract the linearized accessibility tree for a session.

        Returns:
            (tree_text, parsed_elements) tuple.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        try:
            screenshot = await self.capture_screenshot()
        except Exception:
            screenshot = None

        obs: dict[str, Any] = {}
        if screenshot:
            obs["screenshot"] = screenshot

        tree_text = session.aci.linearize_and_annotate_tree(
            obs, show_all_elements=show_all
        )
        session.tree_text = tree_text
        session.screenshot = screenshot
        session.updated_at = datetime.now(timezone.utc)

        elements = self._parse_tree_elements(tree_text)
        return tree_text, elements

    @staticmethod
    def _parse_tree_elements(tree_text: str) -> list[TreeElement]:
        """Parse tab-separated tree text into structured elements."""
        elements: list[TreeElement] = []
        lines = tree_text.strip().split("\n")
        for line in lines[1:]:  # skip header
            parts = line.split("\t")
            if len(parts) >= 4:
                try:
                    elements.append(TreeElement(
                        element_id=int(parts[0]),
                        role=parts[1],
                        title=parts[2],
                        text=parts[3],
                    ))
                except (ValueError, IndexError):
                    pass
        return elements

    # ── Action dispatch ──────────────────────────────────────────────────

    async def dispatch_action(
        self,
        session_id: str,
        action_type: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch an action to a session's ACI and return the generated code.

        Supported actions:
            click, type, scroll, hotkey, open, switch_applications,
            drag_and_drop, hold_and_press, wait, done, fail
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        aci = session.aci
        method = getattr(aci, action_type, None)
        if method is None or not getattr(method, "is_agent_action", False):
            raise ValueError(f"Unknown action type: {action_type}")

        try:
            code = method(**params)
        except Exception as e:
            logger.error("Action %s failed: %s", action_type, e)
            raise

        record = {
            "action_type": action_type,
            "params": params,
            "code": code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        session.action_history.append(record)
        session.updated_at = datetime.now(timezone.utc)

        return record

    async def get_action_history(
        self, session_id: str
    ) -> list[dict[str, Any]]:
        """Get the action history for a session."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        return session.action_history

    async def get_available_actions(self) -> list[dict[str, Any]]:
        """List all available actions with their signatures."""
        aci = _create_aci()
        actions: list[dict[str, Any]] = []
        for name in dir(aci):
            if name.startswith("_"):
                continue
            method = getattr(aci, name, None)
            if method is not None and getattr(method, "is_agent_action", False):
                actions.append({
                    "name": name,
                    "doc": (method.__doc__ or "").strip(),
                })
        return actions