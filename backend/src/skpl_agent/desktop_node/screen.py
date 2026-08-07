"""Screen capture module — multi-backend screenshot and image processing.

Supports multiple capture backends (pyautogui, mss, PIL) and provides
image compression, region capture, and base64 encoding for network transfer.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Cross-platform screen capture with multiple backend support.

    Supports three backends:
    - ``pyautogui``: Simple, cross-platform, slower
    - ``mss``: Fast, multi-monitor support, recommended
    - ``pil``: PIL-based, limited to single monitor

    Usage:
        >>> cap = ScreenCapture(backend="mss", quality=85)
        >>> b64 = cap.capture_base64()  # Full screen, base64 encoded
        >>> b64 = cap.capture_region_base64(0, 0, 800, 600)  # Region
        >>> img = cap.capture_pil()  # PIL Image object
    """

    def __init__(
        self,
        backend: str = "mss",
        quality: int = 85,
        default_format: str = "jpeg",
    ) -> None:
        self._backend = backend
        self._quality = quality
        self._default_format = default_format
        self._mss_instance: Optional[object] = None

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def quality(self) -> int:
        return self._quality

    # ── Public API ───────────────────────────────────────────────────────

    def capture_pil(self, region: Optional[tuple[int, int, int, int]] = None):
        """Capture screen as PIL Image.

        Args:
            region: Optional (x, y, width, height) tuple.

        Returns:
            PIL.Image object.
        """
        if self._backend == "mss":
            return self._capture_mss(region)
        elif self._backend == "pyautogui":
            return self._capture_pyautogui(region)
        else:
            return self._capture_pil(region)

    def capture_base64(
        self,
        region: Optional[tuple[int, int, int, int]] = None,
        img_format: Optional[str] = None,
    ) -> str:
        """Capture screen and return base64-encoded image string.

        Args:
            region: Optional (x, y, width, height) tuple.
            img_format: Image format (jpeg/png). Defaults to self._default_format.

        Returns:
            Base64 encoded image string.
        """
        img = self.capture_pil(region)
        fmt = img_format or self._default_format
        return self._pil_to_base64(img, fmt, self._quality)

    def capture_bytes(
        self,
        region: Optional[tuple[int, int, int, int]] = None,
        img_format: Optional[str] = None,
    ) -> bytes:
        """Capture screen and return raw bytes.

        Args:
            region: Optional (x, y, width, height) tuple.
            img_format: Image format (jpeg/png). Defaults to self._default_format.

        Returns:
            Raw image bytes.
        """
        img = self.capture_pil(region)
        fmt = img_format or self._default_format
        buf = io.BytesIO()
        img.save(buf, format=fmt.upper(), quality=self._quality)
        return buf.getvalue()

    def get_screen_size(self) -> tuple[int, int]:
        """Get primary screen resolution."""
        try:
            import pyautogui
            size = pyautogui.size()
            return (size.width, size.height)
        except Exception:
            try:
                img = self.capture_pil()
                return (img.width, img.height)
            except Exception:
                return (1920, 1080)

    # ── Backend Implementations ──────────────────────────────────────────

    def _capture_mss(self, region: Optional[tuple[int, int, int, int]] = None):
        """Capture using MSS (fast, multi-monitor)."""
        import mss
        import mss.tools

        if self._mss_instance is None:
            self._mss_instance = mss.mss()

        if region:
            x, y, w, h = region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        else:
            monitor = self._mss_instance.monitors[1]  # primary monitor

        sct_img = self._mss_instance.grab(monitor)
        from PIL import Image
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def _capture_pyautogui(self, region: Optional[tuple[int, int, int, int]] = None):
        """Capture using pyautogui."""
        import pyautogui
        from PIL import Image

        if region:
            x, y, w, h = region
            img = pyautogui.screenshot(region=(x, y, w, h))
        else:
            img = pyautogui.screenshot()
        return img

    def _capture_pil(self, region: Optional[tuple[int, int, int, int]] = None):
        """Capture using PIL.ImageGrab (Windows/macOS only)."""
        from PIL import ImageGrab

        if region:
            x, y, w, h = region
            return ImageGrab.grab(bbox=(x, y, x + w, y + h))
        else:
            return ImageGrab.grab()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _pil_to_base64(img, fmt: str, quality: int) -> str:
        """Convert PIL Image to base64 string."""
        buf = io.BytesIO()
        save_format = "JPEG" if fmt.lower() == "jpeg" else fmt.upper()
        img.save(buf, format=save_format, quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def base64_to_pil(b64_string: str):
        """Convert base64 string to PIL Image."""
        from PIL import Image
        data = base64.b64decode(b64_string)
        return Image.open(io.BytesIO(data))

    @staticmethod
    def resize_image(img, max_width: int = 1920, max_height: int = 1080):
        """Resize image to fit within max dimensions while preserving aspect ratio."""
        w, h = img.size
        if w <= max_width and h <= max_height:
            return img
        ratio = min(max_width / w, max_height / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        return img.resize((new_w, new_h), resample=img.Resampling.LANCZOS)