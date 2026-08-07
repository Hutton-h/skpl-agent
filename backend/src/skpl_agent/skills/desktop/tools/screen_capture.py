"""Screen capture — full-screen, region, and active window screenshots.

Provides platform-aware screenshot capabilities using pyautogui
with pywin32 fallback on Windows. All captures are lazy-loaded
to avoid import errors on unsupported platforms.
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Screenshot:
    """A captured screenshot result.

    Attributes:
        width: Image width in pixels.
        height: Image height in pixels.
        format: Image format (always 'png' for base64).
        data_base64: Base64-encoded PNG image data.
        capture_type: Type of capture (fullscreen, region, active_window).
        region: (x, y, w, h) tuple for region captures, None otherwise.
        duration_ms: Time taken to capture.
        error: Error message if capture failed.
    """

    width: int = 0
    height: int = 0
    format: str = "png"
    data_base64: str = ""
    capture_type: str = "fullscreen"
    region: tuple[int, int, int, int] | None = None
    duration_ms: float = 0.0
    error: str = ""


class ScreenCapture:
    """Captures screenshots of the full screen, regions, or active windows.

    Uses pyautogui as the primary backend with fallback to platform-specific
    APIs. All platform-dependent imports are lazy-loaded.

    Usage:
        >>> capture = ScreenCapture()
        >>> screenshot = capture.capture_fullscreen()
        >>> print(f"Captured {screenshot.width}x{screenshot.height}")
        >>> region = capture.capture_region(100, 100, 400, 300)
        >>> window = capture.capture_active_window()
    """

    def __init__(self) -> None:
        self._pyautogui: Optional[object] = None

    # ── Lazy Import Helpers ──────────────────────────────────────────────

    def _get_pyautogui(self):
        """Lazy-load pyautogui with import guard."""
        if self._pyautogui is None:
            try:
                import pyautogui
                self._pyautogui = pyautogui
                logger.debug("pyautogui loaded successfully")
            except ImportError as e:
                logger.error("pyautogui not available: %s", e)
                raise ImportError(
                    "pyautogui is required for screen capture. "
                    "Install with: pip install pyautogui Pillow"
                ) from e
        return self._pyautogui

    def _get_pywin32(self):
        """Lazy-load pywin32 for Windows-specific functionality."""
        try:
            import win32gui
            import win32ui
            import win32con
            return win32gui, win32ui, win32con
        except ImportError:
            logger.error("pywin32 not available on this platform")
            raise ImportError(
                "pywin32 is required for window-specific capture on Windows. "
                "Install with: pip install pywin32"
            )

    # ── Main API ─────────────────────────────────────────────────────────

    def capture_fullscreen(self) -> Screenshot:
        """Capture a screenshot of the entire screen.

        Returns:
            Screenshot object with base64-encoded PNG data.
        """
        start = time.monotonic()

        try:
            pg = self._get_pyautogui()
            img = pg.screenshot()

            data_b64 = self._image_to_base64(img)
            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "Fullscreen captured: %dx%d (%.0fms)",
                img.width, img.height, elapsed,
            )

            return Screenshot(
                width=img.width,
                height=img.height,
                format="png",
                data_base64=data_b64,
                capture_type="fullscreen",
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error("Fullscreen capture failed: %s", e)
            return Screenshot(
                capture_type="fullscreen",
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    def capture_region(self, x: int, y: int, w: int, h: int) -> Screenshot:
        """Capture a screenshot of a specific screen region.

        Args:
            x: Left coordinate of the region.
            y: Top coordinate of the region.
            w: Width of the region.
            h: Height of the region.

        Returns:
            Screenshot object with the captured region.
        """
        start = time.monotonic()

        if w <= 0 or h <= 0:
            return Screenshot(
                capture_type="region",
                region=(x, y, w, h),
                error=f"Invalid region dimensions: {w}x{h}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            pg = self._get_pyautogui()
            img = pg.screenshot(region=(x, y, w, h))

            data_b64 = self._image_to_base64(img)
            elapsed = (time.monotonic() - start) * 1000

            logger.debug(
                "Region captured: (%d,%d %dx%d) (%.0fms)",
                x, y, w, h, elapsed,
            )

            return Screenshot(
                width=img.width,
                height=img.height,
                format="png",
                data_base64=data_b64,
                capture_type="region",
                region=(x, y, w, h),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error("Region capture failed: %s", e)
            return Screenshot(
                capture_type="region",
                region=(x, y, w, h),
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    def capture_active_window(self) -> Screenshot:
        """Capture a screenshot of the currently active window.

        On Windows, uses pywin32 to get the active window bounds.
        On other platforms, falls back to fullscreen capture.

        Returns:
            Screenshot object with the active window capture.
        """
        start = time.monotonic()

        try:
            try:
                win32gui, win32ui, win32con = self._get_pywin32()

                # Get active window handle and bounds
                hwnd = win32gui.GetForegroundWindow()
                rect = win32gui.GetWindowRect(hwnd)
                x, y, right, bottom = rect
                w = right - x
                h = bottom - y

                return self.capture_region(x, y, w, h)

            except ImportError:
                # Fallback: capture fullscreen and log warning
                logger.warning(
                    "pywin32 not available, falling back to fullscreen capture"
                )
                result = self.capture_fullscreen()
                result.capture_type = "active_window_fallback"
                return result

        except Exception as e:
            logger.error("Active window capture failed: %s", e)
            return Screenshot(
                capture_type="active_window",
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    # ── Image Encoding ───────────────────────────────────────────────────

    @staticmethod
    def _image_to_base64(img) -> str:
        """Convert a PIL Image to base64-encoded PNG string.

        Args:
            img: PIL Image object.

        Returns:
            Base64-encoded PNG data string.
        """
        import io

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    # ── Utility ──────────────────────────────────────────────────────────

    def get_screen_size(self) -> tuple[int, int]:
        """Get the current screen resolution.

        Returns:
            Tuple of (width, height) in pixels.
        """
        try:
            pg = self._get_pyautogui()
            return pg.size()
        except Exception as e:
            logger.error("Failed to get screen size: %s", e)
            return (0, 0)