"""Keyboard controller — simulate text input, key presses, and hotkeys.

Provides cross-platform keyboard simulation using pyautogui as the
primary backend. All platform-dependent imports are lazy-loaded.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class KeyboardController:
    """Simulates keyboard input including text typing, key presses, and hotkeys.

    Uses pyautogui for cross-platform keyboard control. All imports are
    lazy-loaded to avoid errors on headless or unsupported systems.

    Usage:
        >>> kb = KeyboardController()
        >>> kb.type_text("Hello, world!")
        >>> kb.press_key("enter")
        >>> kb.hotkey("ctrl", "c")  # Copy
        >>> kb.paste("Some text to paste")
    """

    def __init__(self) -> None:
        self._pyautogui: Optional[object] = None

    # ── Lazy Import ──────────────────────────────────────────────────────

    def _get_pyautogui(self):
        """Lazy-load pyautogui with import guard."""
        if self._pyautogui is None:
            try:
                import pyautogui
                pyautogui.PAUSE = 0.05
                self._pyautogui = pyautogui
                logger.debug("pyautogui loaded successfully for keyboard control")
            except ImportError as e:
                logger.error("pyautogui not available: %s", e)
                raise ImportError(
                    "pyautogui is required for keyboard control. "
                    "Install with: pip install pyautogui"
                ) from e
        return self._pyautogui

    # ── Main API ─────────────────────────────────────────────────────────

    def type_text(self, text: str, interval: float = 0.0) -> None:
        """Type a string of text character by character.

        Args:
            text: The text to type.
            interval: Delay in seconds between each keystroke.
        """
        if not text:
            return

        try:
            pg = self._get_pyautogui()
            pg.typewrite(text, interval=interval)
            logger.debug("Typed text (%d chars, interval=%.2fs)", len(text), interval)
        except Exception as e:
            logger.error("Type text failed: %s", e)

    def press_key(self, key: str, presses: int = 1, interval: float = 0.1) -> None:
        """Press and release a single key.

        Args:
            key: The key to press. Can be a single character or a named
                 key like 'enter', 'tab', 'escape', 'backspace', 'delete',
                 'up', 'down', 'left', 'right', 'f1'-'f12', etc.
            presses: Number of times to press the key.
            interval: Delay between multiple presses.
        """
        try:
            pg = self._get_pyautogui()
            pg.press(key, presses=presses, interval=interval)
            logger.debug("Pressed key: '%s' (%dx)", key, presses)
        except Exception as e:
            logger.error("Press key '%s' failed: %s", key, e)

    def hotkey(self, *keys: str) -> None:
        """Press a combination of keys simultaneously (e.g., ctrl+c).

        Keys are pressed in order, held together, then released in reverse order.

        Args:
            *keys: Variable number of key names to combine.
                   E.g., hotkey('ctrl', 'c') for copy,
                   hotkey('ctrl', 'shift', 'escape') for task manager.

        Usage:
            >>> kb.hotkey("ctrl", "c")       # Copy
            >>> kb.hotkey("ctrl", "v")       # Paste
            >>> kb.hotkey("alt", "tab")      # Switch window
            >>> kb.hotkey("ctrl", "shift", "n")  # New incognito window
        """
        if not keys:
            return

        try:
            pg = self._get_pyautogui()
            pg.hotkey(*keys)
            logger.debug("Hotkey pressed: %s", " + ".join(keys))
        except Exception as e:
            logger.error("Hotkey %s failed: %s", " + ".join(keys), e)

    def paste(self, text: str) -> None:
        """Paste text using the system clipboard (ctrl+v / cmd+v).

        This is more reliable than type_text for large blocks of text
        and preserves formatting.

        Args:
            text: The text to paste via clipboard.
        """
        import platform

        if not text:
            return

        try:
            # Set clipboard content
            self._set_clipboard(text)

            # Use platform-appropriate paste shortcut
            if platform.system() == "Darwin":
                self.hotkey("command", "v")
            else:
                self.hotkey("ctrl", "v")

            logger.debug("Pasted text via clipboard (%d chars)", len(text))
        except Exception as e:
            logger.error("Paste failed: %s", e)

    # ── Clipboard ────────────────────────────────────────────────────────

    @staticmethod
    def _set_clipboard(text: str) -> None:
        """Set the system clipboard content.

        Args:
            text: The text to copy to clipboard.
        """
        import platform
        import subprocess

        system = platform.system()

        try:
            if system == "Windows":
                # Use PowerShell to set clipboard
                cmd = ["powershell", "-Command", "Set-Clipboard", "-Value", text]
                subprocess.run(cmd, capture_output=True, check=True, text=True)
            elif system == "Darwin":
                subprocess.run(["pbcopy"], input=text, text=True, check=True)
            else:
                # Linux: try xclip or xsel
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text, text=True, check=True,
                    )
                except FileNotFoundError:
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=text, text=True, check=True,
                    )
        except subprocess.CalledProcessError as e:
            logger.warning("Could not set clipboard: %s", e)
        except FileNotFoundError:
            logger.warning("No clipboard tool available on this system")

    # ── Advanced ─────────────────────────────────────────────────────────

    def key_down(self, key: str) -> None:
        """Hold down a key without releasing it.

        Useful for key combinations not covered by hotkey().

        Args:
            key: The key to hold down.
        """
        try:
            pg = self._get_pyautogui()
            pg.keyDown(key)
            logger.debug("Key down: '%s'", key)
        except Exception as e:
            logger.error("Key down '%s' failed: %s", key, e)

    def key_up(self, key: str) -> None:
        """Release a previously held key.

        Args:
            key: The key to release.
        """
        try:
            pg = self._get_pyautogui()
            pg.keyUp(key)
            logger.debug("Key up: '%s'", key)
        except Exception as e:
            logger.error("Key up '%s' failed: %s", key, e)

    def write(self, text: str, interval: float = 0.0) -> None:
        """Alias for type_text for compatibility.

        Args:
            text: The text to type.
            interval: Delay between keystrokes.
        """
        self.type_text(text, interval=interval)

    def press_enter(self) -> None:
        """Convenience method to press the Enter key."""
        self.press_key("enter")

    def press_tab(self) -> None:
        """Convenience method to press the Tab key."""
        self.press_key("tab")

    def press_escape(self) -> None:
        """Convenience method to press the Escape key."""
        self.press_key("escape")

    def press_backspace(self, count: int = 1) -> None:
        """Convenience method to press Backspace one or more times.

        Args:
            count: Number of times to press backspace.
        """
        self.press_key("backspace", presses=count)