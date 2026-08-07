"""Window manager — enumerate, focus, minimize, and maximize windows.

Provides cross-platform window management. On Windows, uses pywin32
for window enumeration and control. On other platforms, falls back
to platform-specific tools where available.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Information about a desktop window.

    Attributes:
        title: Window title text.
        handle: Platform-specific window handle (integer on Windows).
        class_name: Window class name.
        is_visible: Whether the window is visible.
        is_minimized: Whether the window is minimized.
        is_maximized: Whether the window is maximized.
        rect: (left, top, right, bottom) pixel coordinates.
        pid: Process ID associated with the window.
    """

    title: str = ""
    handle: int = 0
    class_name: str = ""
    is_visible: bool = True
    is_minimized: bool = False
    is_maximized: bool = False
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)
    pid: int = 0


class WindowManager:
    """Manages desktop windows: list, focus, minimize, maximize.

    Uses pywin32 on Windows for native window operations. Provides
    graceful fallback for unsupported platforms.

    Usage:
        >>> wm = WindowManager()
        >>> windows = wm.list_windows()
        >>> for w in windows[:5]:
        >>>     print(w.title)
        >>> wm.focus_window("Notepad")
        >>> wm.maximize_window("Notepad")
        >>> active = wm.get_active_window()
    """

    def __init__(self) -> None:
        self._win32gui: Optional[object] = None
        self._win32con: Optional[object] = None

    # ── Lazy Import ──────────────────────────────────────────────────────

    def _get_win32(self):
        """Lazy-load pywin32 components."""
        if self._win32gui is None:
            try:
                import win32gui
                import win32con
                self._win32gui = win32gui
                self._win32con = win32con
                logger.debug("pywin32 loaded successfully for window management")
            except ImportError:
                logger.warning(
                    "pywin32 not available. Window management limited to "
                    "basic operations. Install with: pip install pywin32"
                )
                raise
        return self._win32gui, self._win32con

    # ── Main API ─────────────────────────────────────────────────────────

    def list_windows(self, visible_only: bool = True) -> list[WindowInfo]:
        """List all windows currently open on the desktop.

        Args:
            visible_only: If True, only return visible windows.

        Returns:
            List of WindowInfo objects.
        """
        try:
            win32gui, win32con = self._get_win32()
        except ImportError:
            logger.warning("Cannot list windows without pywin32")
            return []

        windows: list[WindowInfo] = []

        def _enum_callback(hwnd: int, _extra: object) -> bool:
            try:
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True

                if visible_only and not win32gui.IsWindowVisible(hwnd):
                    return True

                class_name = win32gui.GetClassName(hwnd)
                rect = win32gui.GetWindowRect(hwnd)

                # Check window state
                placement = win32gui.GetWindowPlacement(hwnd)
                is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
                is_maximized = placement[1] == win32con.SW_SHOWMAXIMIZED

                _, pid = win32gui.GetWindowThreadProcessId(hwnd)

                windows.append(WindowInfo(
                    title=title,
                    handle=hwnd,
                    class_name=class_name,
                    is_visible=win32gui.IsWindowVisible(hwnd),
                    is_minimized=is_minimized,
                    is_maximized=is_maximized,
                    rect=rect,
                    pid=pid,
                ))
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_enum_callback, None)
        except Exception as e:
            logger.error("Window enumeration failed: %s", e)

        logger.debug("Listed %d windows (visible_only=%s)", len(windows), visible_only)
        return windows

    def focus_window(self, title: str) -> bool:
        """Bring a window to the foreground by matching its title.

        Args:
            title: Window title to match (case-insensitive substring match).

        Returns:
            True if the window was found and focused, False otherwise.
        """
        try:
            win32gui, win32con = self._get_win32()
        except ImportError:
            logger.warning("Cannot focus window without pywin32")
            return False

        hwnd = self._find_window_by_title(title)
        if hwnd is None:
            logger.warning("Window not found for focus: '%s'", title)
            return False

        try:
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            win32gui.SetForegroundWindow(hwnd)
            logger.info("Window focused: '%s' (hwnd=%d)", title, hwnd)
            return True
        except Exception as e:
            logger.error("Failed to focus window '%s': %s", title, e)
            return False

    def minimize_window(self, title: str) -> bool:
        """Minimize a window by matching its title.

        Args:
            title: Window title to match (case-insensitive substring match).

        Returns:
            True if the window was found and minimized, False otherwise.
        """
        try:
            win32gui, win32con = self._get_win32()
        except ImportError:
            logger.warning("Cannot minimize window without pywin32")
            return False

        hwnd = self._find_window_by_title(title)
        if hwnd is None:
            logger.warning("Window not found for minimize: '%s'", title)
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            logger.info("Window minimized: '%s' (hwnd=%d)", title, hwnd)
            return True
        except Exception as e:
            logger.error("Failed to minimize window '%s': %s", title, e)
            return False

    def maximize_window(self, title: str) -> bool:
        """Maximize a window by matching its title.

        Args:
            title: Window title to match (case-insensitive substring match).

        Returns:
            True if the window was found and maximized, False otherwise.
        """
        try:
            win32gui, win32con = self._get_win32()
        except ImportError:
            logger.warning("Cannot maximize window without pywin32")
            return False

        hwnd = self._find_window_by_title(title)
        if hwnd is None:
            logger.warning("Window not found for maximize: '%s'", title)
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            logger.info("Window maximized: '%s' (hwnd=%d)", title, hwnd)
            return True
        except Exception as e:
            logger.error("Failed to maximize window '%s': %s", title, e)
            return False

    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active (foreground) window.

        Returns:
            WindowInfo for the active window, or None if unavailable.
        """
        try:
            win32gui, _ = self._get_win32()
        except ImportError:
            logger.warning("Cannot get active window without pywin32")
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            is_visible = win32gui.IsWindowVisible(hwnd)

            placement = win32gui.GetWindowPlacement(hwnd)
            is_minimized = placement[1] == self._win32con.SW_SHOWMINIMIZED
            is_maximized = placement[1] == self._win32con.SW_SHOWMAXIMIZED

            _, pid = win32gui.GetWindowThreadProcessId(hwnd)

            return WindowInfo(
                title=title,
                handle=hwnd,
                class_name=class_name,
                is_visible=is_visible,
                is_minimized=is_minimized,
                is_maximized=is_maximized,
                rect=rect,
                pid=pid,
            )
        except Exception as e:
            logger.error("Failed to get active window: %s", e)
            return None

    def close_window(self, title: str) -> bool:
        """Close a window by sending WM_CLOSE.

        Args:
            title: Window title to match (case-insensitive substring match).

        Returns:
            True if the window was found and close signal sent, False otherwise.
        """
        try:
            win32gui, win32con = self._get_win32()
        except ImportError:
            logger.warning("Cannot close window without pywin32")
            return False

        hwnd = self._find_window_by_title(title)
        if hwnd is None:
            logger.warning("Window not found for close: '%s'", title)
            return False

        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            logger.info("Window close signal sent: '%s' (hwnd=%d)", title, hwnd)
            return True
        except Exception as e:
            logger.error("Failed to close window '%s': %s", title, e)
            return False

    # ── Internal Helpers ─────────────────────────────────────────────────

    def _find_window_by_title(self, title: str) -> int | None:
        """Find a window handle by title substring match.

        Args:
            title: Window title to match (case-insensitive substring).

        Returns:
            Window handle as integer, or None if not found.
        """
        try:
            win32gui, _ = self._get_win32()
        except ImportError:
            return None

        found_handle: int | None = None
        title_lower = title.lower()

        def _enum_callback(hwnd: int, _extra: object) -> bool:
            nonlocal found_handle
            try:
                window_title = win32gui.GetWindowText(hwnd).lower()
                if title_lower in window_title:
                    found_handle = hwnd
                    return False  # Stop enumeration
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_enum_callback, None)
        except Exception as e:
            logger.debug("Window search error: %s", e)

        return found_handle