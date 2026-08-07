"""Mouse controller — simulate mouse movement, clicks, and scrolling.

Provides cross-platform mouse control using pyautogui as the primary
backend. All platform-dependent imports are lazy-loaded.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class MousePosition:
    """Current mouse cursor position.

    Attributes:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
    """

    x: int = 0
    y: int = 0


class MouseController:
    """Controls the mouse cursor with movement, clicks, and scrolling.

    Uses pyautogui for cross-platform mouse control. All imports are
    lazy-loaded to avoid errors on headless or unsupported systems.

    Usage:
        >>> mouse = MouseController()
        >>> mouse.move_to(100, 200)
        >>> mouse.click(100, 200, button='left')
        >>> mouse.double_click(150, 250)
        >>> mouse.scroll(0, -3)  # scroll down 3 "clicks"
    """

    def __init__(self) -> None:
        self._pyautogui: Optional[object] = None

    # ── Lazy Import ──────────────────────────────────────────────────────

    def _get_pyautogui(self):
        """Lazy-load pyautogui with import guard."""
        if self._pyautogui is None:
            try:
                import pyautogui
                # Safety settings
                pyautogui.FAILSAFE = True
                pyautogui.PAUSE = 0.05
                self._pyautogui = pyautogui
                logger.debug("pyautogui loaded successfully for mouse control")
            except ImportError as e:
                logger.error("pyautogui not available: %s", e)
                raise ImportError(
                    "pyautogui is required for mouse control. "
                    "Install with: pip install pyautogui"
                ) from e
        return self._pyautogui

    # ── Main API ─────────────────────────────────────────────────────────

    def move_to(self, x: int, y: int, duration: float = 0.2) -> MousePosition:
        """Move the mouse cursor to the specified coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            duration: Time in seconds for the movement animation.

        Returns:
            MousePosition with the final coordinates.
        """
        try:
            pg = self._get_pyautogui()
            pg.moveTo(x, y, duration=duration)
            logger.debug("Mouse moved to (%d, %d) in %.2fs", x, y, duration)
            return MousePosition(x=x, y=y)
        except Exception as e:
            logger.error("Mouse move_to failed: %s", e)
            return self.get_position()

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: Literal["left", "right", "middle"] = "left",
        clicks: int = 1,
    ) -> MousePosition:
        """Click at the current or specified coordinates.

        Args:
            x: X coordinate to click at (None = current position).
            y: Y coordinate to click at (None = current position).
            button: Mouse button to click ('left', 'right', 'middle').
            clicks: Number of consecutive clicks.

        Returns:
            MousePosition after the click.
        """
        try:
            pg = self._get_pyautogui()

            if x is not None and y is not None:
                pg.click(x, y, button=button, clicks=clicks)
            else:
                pg.click(button=button, clicks=clicks)

            pos = pg.position()
            logger.debug(
                "Mouse %s-click (%dx) at (%d, %d)",
                button, clicks, pos.x, pos.y,
            )
            return MousePosition(x=pos.x, y=pos.y)
        except Exception as e:
            logger.error("Mouse click failed: %s", e)
            return self.get_position()

    def double_click(
        self, x: int | None = None, y: int | None = None,
        button: Literal["left", "right", "middle"] = "left",
    ) -> MousePosition:
        """Perform a double-click at the specified coordinates.

        Args:
            x: X coordinate (None = current position).
            y: Y coordinate (None = current position).
            button: Mouse button to double-click.

        Returns:
            MousePosition after the double-click.
        """
        try:
            pg = self._get_pyautogui()

            if x is not None and y is not None:
                pg.doubleClick(x, y, button=button)
            else:
                pg.doubleClick(button=button)

            pos = pg.position()
            logger.debug("Mouse %s double-click at (%d, %d)", button, pos.x, pos.y)
            return MousePosition(x=pos.x, y=pos.y)
        except Exception as e:
            logger.error("Mouse double_click failed: %s", e)
            return self.get_position()

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: Literal["left", "right", "middle"] = "left",
        duration: float = 0.5,
    ) -> MousePosition:
        """Drag from start coordinates to end coordinates.

        Args:
            start_x: Starting X coordinate.
            start_y: Starting Y coordinate.
            end_x: Ending X coordinate.
            end_y: Ending Y coordinate.
            button: Mouse button to hold during drag.
            duration: Time in seconds for the drag movement.

        Returns:
            MousePosition at the end of the drag.
        """
        try:
            pg = self._get_pyautogui()
            pg.moveTo(start_x, start_y, duration=0.1)
            pg.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)

            pos = pg.position()
            logger.debug(
                "Mouse drag (%d,%d)->(%d,%d) button=%s (%.2fs)",
                start_x, start_y, end_x, end_y, button, duration,
            )
            return MousePosition(x=pos.x, y=pos.y)
        except Exception as e:
            logger.error("Mouse drag failed: %s", e)
            return self.get_position()

    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        """Scroll the mouse wheel.

        Positive dy scrolls up, negative dy scrolls down.
        Positive dx scrolls right, negative dx scrolls left.

        Args:
            dx: Horizontal scroll amount (in "clicks").
            dy: Vertical scroll amount (in "clicks").
        """
        try:
            pg = self._get_pyautogui()

            if dx != 0:
                pg.hscroll(dx)
            if dy != 0:
                pg.scroll(dy)

            logger.debug("Mouse scrolled: dx=%d, dy=%d", dx, dy)
        except Exception as e:
            logger.error("Mouse scroll failed: %s", e)

    def get_position(self) -> MousePosition:
        """Get the current mouse cursor position.

        Returns:
            MousePosition with current coordinates.
        """
        try:
            pg = self._get_pyautogui()
            pos = pg.position()
            return MousePosition(x=pos.x, y=pos.y)
        except Exception as e:
            logger.error("Failed to get mouse position: %s", e)
            return MousePosition()

    def move_relative(self, dx: int, dy: int, duration: float = 0.1) -> MousePosition:
        """Move the mouse relative to its current position.

        Args:
            dx: Horizontal offset in pixels.
            dy: Vertical offset in pixels.
            duration: Time in seconds for the movement.

        Returns:
            MousePosition with the new coordinates.
        """
        try:
            pg = self._get_pyautogui()
            pg.moveRel(dx, dy, duration=duration)

            pos = pg.position()
            logger.debug("Mouse moved relative: (%+d, %+d) -> (%d, %d)", dx, dy, pos.x, pos.y)
            return MousePosition(x=pos.x, y=pos.y)
        except Exception as e:
            logger.error("Mouse move_relative failed: %s", e)
            return self.get_position()

    def get_screen_size(self) -> tuple[int, int]:
        """Get the screen resolution for coordinate bounding.

        Returns:
            Tuple of (width, height) in pixels.
        """
        try:
            pg = self._get_pyautogui()
            return pg.size()
        except Exception as e:
            logger.error("Failed to get screen size: %s", e)
            return (0, 0)