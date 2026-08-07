"""Desktop automation tools package.

Provides screen capture, mouse/keyboard control, window management,
and UI tree extraction tools for the SKPL Agent desktop automation
subsystem.
"""

from skpl_agent.skills.desktop.tools.screen_capture import ScreenCapture, Screenshot
from skpl_agent.skills.desktop.tools.mouse_controller import MouseController, MousePosition
from skpl_agent.skills.desktop.tools.keyboard_controller import KeyboardController
from skpl_agent.skills.desktop.tools.window_manager import WindowManager, WindowInfo
from skpl_agent.skills.desktop.tools.ui_tree_extractor import UITreeExtractor, UIElement

__all__ = [
    "ScreenCapture",
    "Screenshot",
    "MouseController",
    "MousePosition",
    "KeyboardController",
    "WindowManager",
    "WindowInfo",
    "UITreeExtractor",
    "UIElement",
]