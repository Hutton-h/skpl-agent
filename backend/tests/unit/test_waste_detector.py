"""Tests for WasteDetector: wasteful token usage detection."""

import pytest
from skpl_agent.context.waste_detector import WasteDetector, WastePattern


class TestFileReadTracking:
    """Duplicate file read detection."""

    @pytest.fixture
    def detector(self):
        return WasteDetector(duplicate_read_threshold=1)

    def test_first_read_not_wasteful(self, detector):
        detector.record_file_read("src/main.py", 500)
        assert detector.is_wasteful_read("src/main.py") is False

    def test_third_read_detects_waste(self, detector):
        detector.record_file_read("src/main.py", 500)
        detector.record_file_read("src/main.py", 500)
        detector.record_file_read("src/main.py", 500)
        patterns = detector.get_patterns()
        assert len(patterns) >= 1
        assert patterns[0].pattern_type == "duplicate_read"

    def test_read_count(self, detector):
        detector.record_file_read("a.py", 100)
        detector.record_file_read("a.py", 100)
        detector.record_file_read("b.py", 200)
        assert detector.get_read_count("a.py") == 2
        assert detector.get_read_count("b.py") == 1
        assert detector.get_read_count("c.py") == 0

    def test_max_file_reads(self, detector):
        detector = WasteDetector(max_file_reads=2)
        detector.record_file_read("x.py", 100)
        detector.record_file_read("x.py", 100)
        assert detector.is_wasteful_read("x.py") is False
        detector.record_file_read("x.py", 100)
        assert detector.is_wasteful_read("x.py") is True


class TestContextTracking:
    """Redundant context injection detection."""

    def test_first_context_not_redundant(self):
        detector = WasteDetector()
        is_redundant = detector.record_context_injection("sess-1", "context A")
        assert is_redundant is False

    def test_duplicate_context_redundant(self):
        detector = WasteDetector()
        context = "project context with many files..."
        detector.record_context_injection("sess-1", context)
        is_redundant = detector.record_context_injection("sess-1", context)
        assert is_redundant is True
        patterns = detector.get_patterns()
        assert any(p.pattern_type == "redundant_context" for p in patterns)

    def test_different_context_not_redundant(self):
        detector = WasteDetector()
        detector.record_context_injection("sess-1", "context A")
        is_redundant = detector.record_context_injection("sess-1", "context B")
        assert is_redundant is False

    def test_disabled_hashing(self):
        detector = WasteDetector(context_hashing_enabled=False)
        context = "some context"
        detector.record_context_injection("sess-1", context)
        is_redundant = detector.record_context_injection("sess-1", context)
        assert is_redundant is False


class TestOutputTracking:
    """Duplicate tool output detection."""

    def test_first_output_not_duplicate(self):
        detector = WasteDetector()
        is_dup = detector.record_tool_output("grep", "result A")
        assert is_dup is False

    def test_duplicate_output_detected(self):
        detector = WasteDetector()
        output = "search results: found 3 matches"
        detector.record_tool_output("grep", output)
        detector.record_tool_output("grep", "other result")
        is_dup = detector.record_tool_output("grep", output)
        assert is_dup is True
        patterns = detector.get_patterns()
        assert any(p.pattern_type == "duplicate_output" for p in patterns)

    def test_different_tools_independent(self):
        detector = WasteDetector()
        output = "result"
        detector.record_tool_output("grep", output)
        is_dup = detector.record_tool_output("find", output)
        assert is_dup is False


class TestOversizedContext:
    """Oversized context detection."""

    def test_normal_context(self):
        detector = WasteDetector()
        context = "small context" * 10  # ~140 chars
        result = detector.check_context_size(context, max_tokens=1000)
        assert result is None

    def test_oversized_context(self):
        detector = WasteDetector()
        # Create a context that exceeds 100 tokens (~400 chars)
        context = "x" * 500  # ~125 tokens
        result = detector.check_context_size(context, max_tokens=100)
        assert result is not None
        assert result.pattern_type == "oversized_context"
        assert result.severity == "high"


class TestWasteSummary:
    """Waste detection summaries."""

    def test_get_total_waste(self):
        detector = WasteDetector(duplicate_read_threshold=0)
        detector.record_file_read("a.py", 100)
        detector.record_file_read("a.py", 100)
        assert detector.get_total_waste() > 0

    def test_get_waste_summary(self):
        detector = WasteDetector(duplicate_read_threshold=0)
        detector.record_file_read("a.py", 100)
        detector.record_file_read("a.py", 100)
        summary = detector.get_waste_summary()
        assert "duplicate_read" in summary
        assert summary["duplicate_read"] > 0

    def test_empty_summary(self):
        detector = WasteDetector()
        assert detector.get_total_waste() == 0
        assert detector.get_waste_summary() == {}

    def test_reset(self):
        detector = WasteDetector(duplicate_read_threshold=0)
        detector.record_file_read("a.py", 100)
        detector.record_file_read("a.py", 100)
        detector.reset()
        assert detector.get_total_waste() == 0
        assert len(detector.get_patterns()) == 0
        assert detector.get_read_count("a.py") == 0


class TestWastePatternDataclass:
    """WastePattern dataclass."""

    def test_create_pattern(self):
        pattern = WastePattern(
            pattern_type="duplicate_read",
            severity="medium",
            description="File read 3 times",
            tokens_wasted=500,
            file_path="src/main.py",
        )
        assert pattern.pattern_type == "duplicate_read"
        assert pattern.severity == "medium"
        assert pattern.tokens_wasted == 500
        assert pattern.file_path == "src/main.py"
        assert pattern.detected_at is not None