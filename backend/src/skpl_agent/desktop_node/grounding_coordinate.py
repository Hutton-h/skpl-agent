"""Coordinate mapping — screen-to-relative and element-to-click-point.

Provides coordinate transformation utilities for mapping between screen
coordinates and relative coordinates, calculating click points from
UI element bounding boxes, and normalizing coordinates across different
screen resolutions.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CoordinateMapper:
    """Maps between screen coordinates and relative coordinates.

    Provides coordinate transformation utilities for desktop automation:
    - Screen coordinates to relative (0.0-1.0) coordinates
    - Relative coordinates to screen coordinates
    - Element bounding box to click point calculation
    - Coordinate normalization across different screen resolutions

    Usage:
        >>> mapper = CoordinateMapper(screen_width=1920, screen_height=1080)
        >>> rel_x, rel_y = mapper.screen_to_relative(960, 540)
        >>> (0.5, 0.5)
        >>> screen_x, screen_y = mapper.relative_to_screen(0.5, 0.5)
        >>> (960, 540)
        >>> point = mapper.element_to_click_point({
        ...     "position": (100, 200),
        ...     "size": (50, 30),
        ... })
        >>> (125, 215)
    """

    def __init__(
        self,
        screen_width: int = 1920,
        screen_height: int = 1080,
        margin: int = 0,
    ) -> None:
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._margin = margin

    @property
    def screen_width(self) -> int:
        """Return the screen width."""
        return self._screen_width

    @screen_width.setter
    def screen_width(self, value: int) -> None:
        """Set the screen width."""
        if value <= 0:
            raise ValueError("Screen width must be positive")
        self._screen_width = value

    @property
    def screen_height(self) -> int:
        """Return the screen height."""
        return self._screen_height

    @screen_height.setter
    def screen_height(self, value: int) -> None:
        """Set the screen height."""
        if value <= 0:
            raise ValueError("Screen height must be positive")
        self._screen_height = value

    def update_screen_size(self, width: int, height: int) -> None:
        """Update the screen dimensions.

        Args:
            width: Screen width in pixels.
            height: Screen height in pixels.
        """
        self._screen_width = width
        self._screen_height = height
        logger.debug("Screen size updated to %dx%d", width, height)

    def detect_screen_size(self) -> tuple[int, int]:
        """Auto-detect screen size using pyautogui.

        Returns:
            (width, height) tuple.
        """
        try:
            import pyautogui
            size = pyautogui.size()
            self._screen_width = size.width
            self._screen_height = size.height
            logger.debug("Detected screen size: %dx%d", size.width, size.height)
        except ImportError:
            logger.warning("pyautogui not available, using default screen size")
        except Exception as e:
            logger.warning("Failed to detect screen size: %s", e)
        return (self._screen_width, self._screen_height)

    # ── Coordinate transformations ───────────────────────────────────────

    def screen_to_relative(
        self,
        x: int | float,
        y: int | float,
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> tuple[float, float]:
        """Convert screen coordinates to relative coordinates (0-1).

        Args:
            x: Screen X coordinate.
            y: Screen Y coordinate.
            screen_w: Screen width (uses self._screen_width if None).
            screen_h: Screen height (uses self._screen_height if None).

        Returns:
            (rx, ry) relative coordinates in range [0, 1].
        """
        w = screen_w or self._screen_width
        h = screen_h or self._screen_height

        if w <= 0 or h <= 0:
            raise ValueError("Screen dimensions must be positive")

        rx = max(0.0, min(1.0, float(x) / w))
        ry = max(0.0, min(1.0, float(y) / h))
        return (rx, ry)

    def relative_to_screen(
        self,
        rx: float,
        ry: float,
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> tuple[int, int]:
        """Convert relative coordinates (0-1) to screen coordinates.

        Args:
            rx: Relative X coordinate (0.0-1.0).
            ry: Relative Y coordinate (0.0-1.0).
            screen_w: Screen width (uses self._screen_width if None).
            screen_h: Screen height (uses self._screen_height if None).

        Returns:
            (x, y) screen coordinates.
        """
        w = screen_w or self._screen_width
        h = screen_h or self._screen_height

        if w <= 0 or h <= 0:
            raise ValueError("Screen dimensions must be positive")

        x = int(round(rx * w))
        y = int(round(ry * h))
        return (x, y)

    def normalize_bbox(
        self,
        bbox: list[int] | tuple[int, int, int, int],
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> tuple[float, float, float, float]:
        """Normalize a bounding box to relative coordinates.

        Args:
            bbox: [x1, y1, x2, y2] or (x1, y1, x2, y2) in screen pixels.
            screen_w: Screen width.
            screen_h: Screen height.

        Returns:
            (rx1, ry1, rx2, ry2) in relative coordinates.
        """
        x1, y1, x2, y2 = bbox
        rx1, ry1 = self.screen_to_relative(x1, y1, screen_w, screen_h)
        rx2, ry2 = self.screen_to_relative(x2, y2, screen_w, screen_h)
        return (rx1, ry1, rx2, ry2)

    def denormalize_bbox(
        self,
        norm_bbox: tuple[float, float, float, float],
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> tuple[int, int, int, int]:
        """Convert a normalized bounding box to screen coordinates.

        Args:
            norm_bbox: (rx1, ry1, rx2, ry2) in relative coordinates.
            screen_w: Screen width.
            screen_h: Screen height.

        Returns:
            (x1, y1, x2, y2) in screen pixels.
        """
        rx1, ry1, rx2, ry2 = norm_bbox
        x1, y1 = self.relative_to_screen(rx1, ry1, screen_w, screen_h)
        x2, y2 = self.relative_to_screen(rx2, ry2, screen_w, screen_h)
        return (x1, y1, x2, y2)

    # ── Element click point calculations ─────────────────────────────────

    def element_to_click_point(
        self,
        element: dict[str, Any],
    ) -> tuple[int, int] | None:
        """Calculate the center click point of a UI element.

        Supports multiple element formats:
        - ``{"position": (x, y), "size": (w, h)}``
        - ``{"bbox": [x1, y1, x2, y2]}``
        - ``{"x": x, "y": y, "width": w, "height": h}``

        Args:
            element: UI element dict with position/size or bbox.

        Returns:
            (x, y) center click point, or None if invalid.
        """
        # Format 1: position + size
        pos = element.get("position")
        size = element.get("size")
        if pos is not None and size is not None:
            x = int(pos[0] + size[0] // 2)
            y = int(pos[1] + size[1] // 2)
            return (x, y)

        # Format 2: bbox
        bbox = element.get("bbox")
        if bbox is not None and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            x = int((x1 + x2) / 2)
            y = int((y1 + y2) / 2)
            return (x, y)

        # Format 3: x, y, width, height
        x = element.get("x")
        y = element.get("y")
        w = element.get("width")
        h = element.get("height")
        if x is not None and y is not None and w is not None and h is not None:
            return (int(x + w // 2), int(y + h // 2))

        return None

    def element_to_relative_click_point(
        self,
        element: dict[str, Any],
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> tuple[float, float] | None:
        """Calculate the relative click point of a UI element.

        Args:
            element: UI element dict with position/size or bbox.
            screen_w: Screen width.
            screen_h: Screen height.

        Returns:
            (rx, ry) relative click point, or None if invalid.
        """
        point = self.element_to_click_point(element)
        if point is None:
            return None
        return self.screen_to_relative(point[0], point[1], screen_w, screen_h)

    def elements_to_click_points(
        self,
        elements: list[dict[str, Any]],
    ) -> list[tuple[int, int]]:
        """Calculate click points for a list of elements.

        Args:
            elements: List of UI element dicts.

        Returns:
            List of (x, y) click points.
        """
        points: list[tuple[int, int]] = []
        for elem in elements:
            point = self.element_to_click_point(elem)
            if point is not None:
                points.append(point)
        return points

    def is_within_screen(
        self,
        x: int,
        y: int,
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> bool:
        """Check if a point is within the screen bounds.

        Args:
            x: X coordinate.
            y: Y coordinate.
            screen_w: Screen width.
            screen_h: Screen height.

        Returns:
            True if the point is within screen bounds.
        """
        w = screen_w or self._screen_width
        h = screen_h or self._screen_height
        m = self._margin
        return m <= x <= w - m and m <= y <= h - m

    def clamp_to_screen(
        self,
        x: int,
        y: int,
        screen_w: int | None = None,
        screen_h: int | None = None,
    ) -> tuple[int, int]:
        """Clamp coordinates to within screen bounds.

        Args:
            x: X coordinate.
            y: Y coordinate.
            screen_w: Screen width.
            screen_h: Screen height.

        Returns:
            (clamped_x, clamped_y) within screen bounds.
        """
        w = screen_w or self._screen_width
        h = screen_h or self._screen_height
        m = self._margin
        cx = max(m, min(w - m, x))
        cy = max(m, min(h - m, y))
        return (cx, cy)

    # ── Bounding box utilities ───────────────────────────────────────────

    def bbox_area(self, bbox: list[int] | tuple[int, int, int, int]) -> int:
        """Calculate the area of a bounding box.

        Args:
            bbox: [x1, y1, x2, y2] in screen pixels.

        Returns:
            Area in square pixels.
        """
        x1, y1, x2, y2 = bbox
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        return w * h

    def bbox_center(self, bbox: list[int] | tuple[int, int, int, int]) -> tuple[int, int]:
        """Calculate the center of a bounding box.

        Args:
            bbox: [x1, y1, x2, y2] in screen pixels.

        Returns:
            (cx, cy) center coordinates.
        """
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    def bbox_iou(
        self,
        bbox1: list[int] | tuple[int, int, int, int],
        bbox2: list[int] | tuple[int, int, int, int],
    ) -> float:
        """Calculate Intersection over Union (IoU) of two bounding boxes.

        Args:
            bbox1: First bounding box [x1, y1, x2, y2].
            bbox2: Second bounding box [x1, y1, x2, y2].

        Returns:
            IoU value in range [0, 1].
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # Intersection
        ix1 = max(x1_1, x1_2)
        iy1 = max(y1_1, y1_2)
        ix2 = min(x2_1, x2_2)
        iy2 = min(y2_1, y2_2)

        inter_w = max(0, ix2 - ix1)
        inter_h = max(0, iy2 - iy1)
        inter_area = inter_w * inter_h

        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = area1 + area2 - inter_area

        if union_area <= 0:
            return 0.0

        return inter_area / union_area

    def bbox_contains_point(
        self,
        bbox: list[int] | tuple[int, int, int, int],
        x: int,
        y: int,
    ) -> bool:
        """Check if a point is inside a bounding box.

        Args:
            bbox: [x1, y1, x2, y2] bounding box.
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if the point is inside the bounding box.
        """
        x1, y1, x2, y2 = bbox
        return x1 <= x <= x2 and y1 <= y <= y2

    def bbox_intersects(
        self,
        bbox1: list[int] | tuple[int, int, int, int],
        bbox2: list[int] | tuple[int, int, int, int],
    ) -> bool:
        """Check if two bounding boxes intersect.

        Args:
            bbox1: First bounding box.
            bbox2: Second bounding box.

        Returns:
            True if the boxes intersect.
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        return x1_1 < x2_2 and x2_1 > x1_2 and y1_1 < y2_2 and y2_1 > y1_2

    # ── Scale-aware mapping ──────────────────────────────────────────────

    def scale_coordinates(
        self,
        x: int | float,
        y: int | float,
        from_width: int,
        from_height: int,
        to_width: int,
        to_height: int,
    ) -> tuple[int, int]:
        """Scale coordinates from one resolution to another.

        Useful for mapping coordinates from a screenshot of a different
        size back to the actual screen.

        Args:
            x: X coordinate in source resolution.
            y: Y coordinate in source resolution.
            from_width: Source width.
            from_height: Source height.
            to_width: Target width.
            to_height: Target height.

        Returns:
            (scaled_x, scaled_y) in target resolution.
        """
        sx = int(round(float(x) * to_width / from_width))
        sy = int(round(float(y) * to_height / from_height))
        return (sx, sy)

    def scale_bbox(
        self,
        bbox: list[int] | tuple[int, int, int, int],
        from_width: int,
        from_height: int,
        to_width: int,
        to_height: int,
    ) -> tuple[int, int, int, int]:
        """Scale a bounding box from one resolution to another.

        Args:
            bbox: [x1, y1, x2, y2] in source resolution.
            from_width: Source width.
            from_height: Source height.
            to_width: Target width.
            to_height: Target height.

        Returns:
            (x1, y1, x2, y2) in target resolution.
        """
        x1, y1, x2, y2 = bbox
        sx1, sy1 = self.scale_coordinates(x1, y1, from_width, from_height, to_width, to_height)
        sx2, sy2 = self.scale_coordinates(x2, y2, from_width, from_height, to_width, to_height)
        return (sx1, sy1, sx2, sy2)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_coordinate_mapper(
    screen_width: int = 1920,
    screen_height: int = 1080,
    auto_detect: bool = False,
    **kwargs: Any,
) -> CoordinateMapper:
    """Create a CoordinateMapper instance.

    Args:
        screen_width: Screen width (used if auto_detect is False).
        screen_height: Screen height (used if auto_detect is False).
        auto_detect: If True, auto-detect screen size using pyautogui.
        **kwargs: Additional keyword arguments.

    Returns:
        CoordinateMapper instance.
    """
    mapper = CoordinateMapper(
        screen_width=screen_width,
        screen_height=screen_height,
    )
    if auto_detect:
        mapper.detect_screen_size()
    return mapper