"""SKPL Agent Desktop Automation (Agent-S Computer Use Integration).

Provides Windows/macOS/Linux desktop automation capabilities adapted from
Agent-S, including UIA tree extraction, OCR overlay, and pyautogui-based
action execution.

Architecture:
    ACI (Actionable Context Interface) — base abstraction
        ├── WindowsACI     — pywinauto + UIA backend
        ├── MacOSACI       — (future) Accessibility API
        └── LinuxOSACI     — (future) AT-SPI

Typical usage:
    >>> from skpl_agent.desktop_automation import WindowsACI
    >>> aci = WindowsACI()
    >>> tree = aci.linearize_and_annotate_tree(obs)
    >>> action_code = aci.click(element_id=3)
"""

from skpl_agent.desktop_automation._aci import ACI, Action, ActionResult, UIElement, agent_action
from skpl_agent.desktop_automation._windows_aci import WindowsACI, UIElement as WindowsUIElement
from skpl_agent.desktop_automation.permission import (
    DesktopPermission,
    PermissionBehavior,
    PermissionContext,
    PermissionDecision,
    get_default_permission,
)

__all__ = [
    "ACI",
    "Action",
    "ActionResult",
    "agent_action",
    "WindowsACI",
    "UIElement",
    "DesktopPermission",
    "PermissionBehavior",
    "PermissionContext",
    "PermissionDecision",
    "get_default_permission",
]