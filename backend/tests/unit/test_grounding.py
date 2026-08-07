"""Tests for grounding modules."""

from __future__ import annotations

import pytest

from skpl_agent.desktop_node.grounding_coordinate import CoordinateMapper


class TestCoordinateMapper:
    """Tests for CoordinateMapper."""

    def test_map_coordinates_same_size(self) -> None:
        """Mapping coordinates when source and target sizes are identical."""
        mapper = CoordinateMapper(source_width=1920, source_height=1080,
                                  target_width=1920, target_height=1080)
        x, y = mapper.map(100, 200)
        assert x == 100
        assert y == 200

    def test_map_coordinates_scaled_down(self) -> None:
        """Mapping coordinates from larger to smaller screen."""
        mapper = CoordinateMapper(source_width=1920, source_height=1080,
                                  target_width=960, target_height=540)
        x, y = mapper.map(100, 200)
        assert x == 50
        assert y == 100

    def test_map_coordinates_scaled_up(self) -> None:
        """Mapping coordinates from smaller to larger screen."""
        mapper = CoordinateMapper(source_width=960, source_height=540,
                                  target_width=1920, target_height=1080)
        x, y = mapper.map(50, 100)
        assert x == 100
        assert y == 200

    def test_map_coordinates_respect_bounds(self) -> None:
        """Mapped coordinates are clamped to target bounds."""
        mapper = CoordinateMapper(source_width=1920, source_height=1080,
                                  target_width=800, target_height=600)

        # Map a point that exceeds the target
        x, y = mapper.map(1920, 1080)
        assert x <= 800
        assert y <= 600

    def test_map_origin(self) -> None:
        """Origin (0,0) maps to (0,0)."""
        mapper = CoordinateMapper(source_width=1920, source_height=1080,
                                  target_width=800, target_height=600)
        x, y = mapper.map(0, 0)
        assert x == 0
        assert y == 0


class TestGroundingPipeline:
    """Tests for the grounding pipeline (coordinate mapping, OCR, UI-TARS)."""

    def test_grounding_module_imports(self) -> None:
        """All grounding modules can be imported."""
        from skpl_agent.desktop_node.grounding_coordinate import CoordinateMapper
        from skpl_agent.desktop_node.grounding_ocr import OCRGrounding
        from skpl_agent.desktop_node.grounding_ui_tars import UITARSGrounding

        assert CoordinateMapper is not None
        assert OCRGrounding is not None
        assert UITARSGrounding is not None

    def test_ocr_grounding_creation(self) -> None:
        """OCRGrounding can be instantiated."""
        from skpl_agent.desktop_node.grounding_ocr import OCRGrounding
        grounding = OCRGrounding()
        assert grounding is not None

    def test_ui_tars_grounding_creation(self) -> None:
        """UITARSGrounding can be instantiated."""
        from skpl_agent.desktop_node.grounding_ui_tars import UITARSGrounding
        grounding = UITARSGrounding()
        assert grounding is not None

    def test_ocr_grounding_has_required_methods(self) -> None:
        """OCRGrounding has required interface methods."""
        from skpl_agent.desktop_node.grounding_ocr import OCRGrounding
        grounding = OCRGrounding()
        assert hasattr(grounding, 'detect_text')
        assert hasattr(grounding, 'find_element')

    def test_ui_tars_grounding_has_required_methods(self) -> None:
        """UITARSGrounding has required interface methods."""
        from skpl_agent.desktop_node.grounding_ui_tars import UITARSGrounding
        grounding = UITARSGrounding()
        assert hasattr(grounding, 'detect')
        assert hasattr(grounding, 'locate')