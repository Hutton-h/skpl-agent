"""Tests for BugMatcher: fingerprinting and deduplication."""

import pytest
from skpl_agent.context.bug_matcher import BugMatcher


class TestFingerprint:
    """Fingerprint computation."""

    @pytest.fixture
    def matcher(self):
        return BugMatcher()

    def test_compute_fingerprint(self, matcher):
        fp = matcher.compute_fingerprint(
            error_type="SyntaxError",
            error_message="invalid syntax",
        )
        assert len(fp) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in fp)

    def test_same_error_same_fingerprint(self, matcher):
        fp1 = matcher.compute_fingerprint(
            error_type="ValueError",
            error_message="invalid value",
        )
        fp2 = matcher.compute_fingerprint(
            error_type="ValueError",
            error_message="invalid value",
        )
        assert fp1 == fp2

    def test_different_type_different_fingerprint(self, matcher):
        fp1 = matcher.compute_fingerprint(error_type="SyntaxError", error_message="error")
        fp2 = matcher.compute_fingerprint(error_type="ValueError", error_message="error")
        assert fp1 != fp2

    def test_fingerprint_normalizes_line_numbers(self, matcher):
        fp1 = matcher.compute_fingerprint(
            error_type="Error",
            error_message="error at line 10",
        )
        fp2 = matcher.compute_fingerprint(
            error_type="Error",
            error_message="error at line 42",
        )
        # After normalization, both should be "error at line N"
        assert fp1 == fp2

    def test_fingerprint_normalizes_file_paths(self, matcher):
        fp1 = matcher.compute_fingerprint(
            error_type="Error",
            error_message="error in file 'src/main.py'",
        )
        fp2 = matcher.compute_fingerprint(
            error_type="Error",
            error_message="error in file 'lib/utils.py'",
        )
        assert fp1 == fp2

    def test_fingerprint_normalizes_uuids(self, matcher):
        fp1 = matcher.compute_fingerprint(
            error_type="Error",
            error_message="task 12345678-1234-1234-1234-123456789abc failed",
        )
        fp2 = matcher.compute_fingerprint(
            error_type="Error",
            error_message="task 87654321-4321-4321-4321-cba987654321 failed",
        )
        assert fp1 == fp2


class TestDeduplication:
    """Duplicate detection."""

    @pytest.fixture
    def matcher(self):
        return BugMatcher()

    def test_exact_duplicate(self, matcher):
        from dataclasses import dataclass

        @dataclass
        class FakeBug:
            id: str
            fingerprint: str
            error_message: str

        bug1 = FakeBug(
            id="bug-1",
            fingerprint=matcher.compute_fingerprint("Error", "test error"),
            error_message="test error",
        )
        bug2_fp = matcher.compute_fingerprint("Error", "test error")
        dup = matcher.find_duplicate(bug2_fp, "test error", [bug1])
        assert dup == "bug-1"

    def test_no_duplicate(self, matcher):
        from dataclasses import dataclass

        @dataclass
        class FakeBug:
            id: str
            fingerprint: str
            error_message: str

        bug1 = FakeBug(
            id="bug-1",
            fingerprint=matcher.compute_fingerprint("Error", "error type A"),
            error_message="error type A",
        )
        fp2 = matcher.compute_fingerprint("Error", "completely different error")
        dup = matcher.find_duplicate(fp2, "completely different error", [bug1])
        assert dup is None

    def test_empty_bugs(self, matcher):
        fp = matcher.compute_fingerprint("Error", "test")
        assert matcher.find_duplicate(fp, "test", []) is None

    def test_similar_message(self, matcher):
        from dataclasses import dataclass

        @dataclass
        class FakeBug:
            id: str
            fingerprint: str
            error_message: str

        bug1 = FakeBug(
            id="bug-1",
            fingerprint=matcher.compute_fingerprint("Error", "connection timeout after 30 seconds"),
            error_message="connection timeout after 30 seconds",
        )
        fp2 = matcher.compute_fingerprint("Error", "connection timeout after 60 seconds")
        dup = matcher.find_duplicate(fp2, "connection timeout after 60 seconds", [bug1])
        # Should match via Jaccard similarity after normalization
        assert dup == "bug-1"


class TestSimilarity:
    """Jaccard similarity computation."""

    @pytest.fixture
    def matcher(self):
        return BugMatcher()

    def test_identical_strings(self, matcher):
        # Use private method for testing
        sim = matcher._jaccard_similarity("hello world", "hello world")
        assert sim == 1.0

    def test_completely_different(self, matcher):
        sim = matcher._jaccard_similarity("hello world", "foo bar baz")
        assert sim == 0.0

    def test_partial_overlap(self, matcher):
        sim = matcher._jaccard_similarity("hello world foo", "hello world bar")
        # words: {hello, world, foo} vs {hello, world, bar}
        # intersection: {hello, world} = 2, union: {hello, world, foo, bar} = 4
        assert sim == 0.5

    def test_empty_strings(self, matcher):
        assert matcher._jaccard_similarity("", "") == 1.0
        assert matcher._jaccard_similarity("hello", "") == 0.0
        assert matcher._jaccard_similarity("", "hello") == 0.0


class TestNormalization:
    """Message normalization."""

    @pytest.fixture
    def matcher(self):
        return BugMatcher()

    def test_normalize_line_numbers(self, matcher):
        msg = "Error at line 42 in module"
        normalized = matcher._normalize_message(msg)
        assert "42" not in normalized
        # After lowercasing, "N" becomes "n"
        assert "n" in normalized

    def test_normalize_file_paths(self, matcher):
        msg = "Error in 'src/main.py' at line 10"
        normalized = matcher._normalize_message(msg)
        assert "src/main.py" not in normalized
        # After lowercasing, "[FILE]" becomes "[file]"
        assert "[file]" in normalized

    def test_normalize_memory_addresses(self, matcher):
        msg = "Segmentation fault at 0x7fff5fbff8c0"
        normalized = matcher._normalize_message(msg)
        assert "0x7fff5fbff8c0" not in normalized
        # After lowercasing, "0xADDR" becomes "0xaddr"
        assert "0xaddr" in normalized

    def test_normalize_uuids(self, matcher):
        msg = "Task a1b2c3d4-e5f6-7890-abcd-ef1234567890 failed"
        normalized = matcher._normalize_message(msg)
        assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" not in normalized
        # After lowercasing, "[UUID]" becomes "[uuid]"
        assert "[uuid]" in normalized

    def test_normalize_timestamps(self, matcher):
        msg = "Failed at 2024-01-15T10:30:00Z"
        normalized = matcher._normalize_message(msg)
        assert "2024-01-15T10:30:00Z" not in normalized
        # After lowercasing, "[TIMESTAMP]" becomes "[timestamp]"
        assert "[timestamp]" in normalized

    def test_normalize_lowercase(self, matcher):
        msg = "ERROR: Something Went Wrong"
        normalized = matcher._normalize_message(msg)
        assert normalized == normalized.lower()


class TestFindSimilar:
    """Find similar bugs."""

    @pytest.fixture
    def matcher(self):
        return BugMatcher()

    def test_find_similar(self, matcher):
        from dataclasses import dataclass

        @dataclass
        class FakeBug:
            id: str
            error_message: str

        bugs = [
            FakeBug(id="b1", error_message="Connection timeout after 30 seconds"),
            FakeBug(id="b2", error_message="File not found: config.json"),
            FakeBug(id="b3", error_message="Connection timeout after 60 seconds"),
        ]
        results = matcher.find_similar("Connection timeout after 45 seconds", bugs)
        assert len(results) >= 2
        # b1 and b3 should be similar
        ids = [r[0] for r in results]
        assert "b1" in ids
        assert "b3" in ids

    def test_find_similar_no_match(self, matcher):
        from dataclasses import dataclass

        @dataclass
        class FakeBug:
            id: str
            error_message: str

        bugs = [
            FakeBug(id="b1", error_message="Syntax error in parser"),
            FakeBug(id="b2", error_message="Null pointer dereference"),
        ]
        results = matcher.find_similar("Network connection refused", bugs)
        assert len(results) == 0