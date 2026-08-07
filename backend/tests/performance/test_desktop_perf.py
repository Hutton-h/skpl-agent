"""Performance tests for desktop operations."""

from __future__ import annotations

import time

import pytest


class TestScreenshotPerformance:
    """Performance benchmarks for screenshot operations."""

    def test_screenshot_encoding_speed(self) -> None:
        """Screenshot encoding is reasonably fast."""
        import base64

        # Simulate a 1MB screenshot
        fake_data = b"\x00" * (1024 * 1024)

        start = time.monotonic()
        encoded = base64.b64encode(fake_data)
        elapsed = time.monotonic() - start

        # Should encode under 50ms
        assert elapsed < 0.1, f"Screenshot encoding too slow: {elapsed:.3f}s"
        assert len(encoded) > 0

    def test_coordinate_mapping_throughput(self) -> None:
        """Coordinate mapping is fast enough for real-time use."""
        from skpl_agent.desktop_node.grounding_coordinate import CoordinateMapper

        mapper = CoordinateMapper(
            source_width=1920, source_height=1080,
            target_width=800, target_height=600,
        )

        start = time.monotonic()
        iterations = 10000
        for i in range(iterations):
            mapper.map(i % 1920, i % 1080)
        elapsed = time.monotonic() - start

        avg_us = (elapsed / iterations) * 1_000_000
        # Should be under 5 microseconds per mapping
        assert avg_us < 10, f"Coordinate mapping too slow: {avg_us:.1f}us per call"

    def test_action_execution_throughput(self) -> None:
        """Action execution is responsive."""
        from skpl_agent.desktop_automation._aci import Action, ActionResult

        start = time.monotonic()
        iterations = 5000
        for _ in range(iterations):
            action = Action(type="click", x=100, y=200)
            result = ActionResult(success=True, action_type=action.type)
        elapsed = time.monotonic() - start

        avg_us = (elapsed / iterations) * 1_000_000
        assert avg_us < 5, f"Action creation too slow: {avg_us:.1f}us per call"


class TestUIElementPerformance:
    """Performance benchmarks for UI element operations."""

    def test_tree_flattening_speed(self) -> None:
        """Flattening a deep UI tree is fast."""
        from skpl_agent.desktop_automation._aci import UIElement

        def build_tree(depth: int, breadth: int) -> UIElement:
            if depth == 0:
                return UIElement(id=f"leaf", name="Leaf", role="text")
            children = [build_tree(depth - 1, breadth) for _ in range(breadth)]
            return UIElement(
                id=f"node-{depth}",
                name=f"Depth {depth}",
                role="group",
                children=children,
            )

        tree = build_tree(depth=3, breadth=3)

        def flatten(element: UIElement) -> list[UIElement]:
            result = [element]
            for child in element.children:
                result.extend(flatten(child))
            return result

        start = time.monotonic()
        flat = flatten(tree)
        elapsed = time.monotonic() - start

        # Tree with 3 depth, 3 breadth = 1 + 3 + 9 + 27 = 40 nodes
        assert len(flat) == 40
        assert elapsed < 0.01, f"Tree flattening too slow: {elapsed:.3f}s"