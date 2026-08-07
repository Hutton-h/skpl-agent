"""Tests for TokenEstimator: token count estimation and cost calculation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from skpl_agent.context.token_estimator import (
    ContentType,
    TokenEstimator,
    estimate_tokens,
    estimate_file_tokens,
)


class TestTokenEstimatorCount:
    """Token count estimation."""

    @pytest.fixture
    def estimator(self) -> TokenEstimator:
        return TokenEstimator()

    def test_empty_string(self, estimator: TokenEstimator) -> None:
        """Empty string returns 0 tokens."""
        assert estimator.count("") == 0

    def test_short_text(self, estimator: TokenEstimator) -> None:
        """Short text returns reasonable token count."""
        tokens = estimator.count("Hello, world!")
        assert tokens > 0
        assert tokens < 10

    def test_long_text(self, estimator: TokenEstimator) -> None:
        """Long text returns proportionally more tokens."""
        short = estimator.count("Hello")
        long_text = "Hello " * 100
        long_tokens = estimator.count(long_text)
        assert long_tokens > short

    def test_python_code_ratio(self, estimator: TokenEstimator) -> None:
        """Python code uses language-specific ratio."""
        code = "def foo(x: int) -> str:\n    return str(x)\n"
        tokens = estimator.count(code, language="python")
        assert tokens > 0

    def test_unknown_language_fallback(self, estimator: TokenEstimator) -> None:
        """Unknown language falls back to content type detection."""
        tokens = estimator.count("def foo(): pass", language="unknown_lang")
        assert tokens > 0

    def test_none_language(self, estimator: TokenEstimator) -> None:
        """None language uses content type detection."""
        tokens = estimator.count("Some prose text with punctuation.")
        assert tokens > 0


class TestTokenEstimatorFile:
    """File token counting."""

    @pytest.fixture
    def estimator(self) -> TokenEstimator:
        return TokenEstimator()

    def test_count_file(self, estimator: TokenEstimator) -> None:
        """Counts tokens in a file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("def hello():\n    print('hello world')\n")
            f.flush()
            f.close()
            tokens = estimator.count_file(f.name)
            Path(f.name).unlink()
            assert tokens > 0

    def test_count_file_nonexistent(self, estimator: TokenEstimator) -> None:
        """Nonexistent file returns 0 tokens."""
        tokens = estimator.count_file("/nonexistent/file.py")
        assert tokens == 0

    def test_count_batch(self, estimator: TokenEstimator) -> None:
        """Batch count returns list of token counts."""
        texts = ["hello", "world", "def foo(): pass"]
        counts = estimator.count_batch(texts, language="python")
        assert len(counts) == 3
        assert all(c > 0 for c in counts)


class TestContentTypeDetection:
    """Content type detection heuristics."""

    def test_detect_code(self) -> None:
        """Detects code content type."""
        text = "def foo():\n    x = 1 + 2\n    return x\n"
        ct = TokenEstimator._detect_content_type(text)
        assert ct == ContentType.CODE

    def test_detect_prose(self) -> None:
        """Detects prose content type."""
        text = (
            "This is a long paragraph of prose text. It contains many sentences "
            "with punctuation, commas, and periods. The text is descriptive and "
            "narrative in nature, not code-like at all."
        )
        ct = TokenEstimator._detect_content_type(text)
        assert ct == ContentType.PROSE

    def test_detect_mixed(self) -> None:
        """Detects mixed content type."""
        text = "Here is some text. def foo(): pass. More text here."
        ct = TokenEstimator._detect_content_type(text)
        assert ct == ContentType.MIXED


class TestCostEstimation:
    """Cost estimation for various models."""

    @pytest.fixture
    def estimator(self) -> TokenEstimator:
        return TokenEstimator()

    def test_gpt4o_cost(self, estimator: TokenEstimator) -> None:
        """Estimates GPT-4o cost."""
        cost = estimator.estimate_cost(1000, 500, "gpt-4o")
        assert cost > 0
        # 1000 input * $2.50/1M + 500 output * $10.00/1M
        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert cost == pytest.approx(expected, rel=0.01)

    def test_claude_cost(self, estimator: TokenEstimator) -> None:
        """Estimates Claude cost."""
        cost = estimator.estimate_cost(1000, 500, "claude-3.5-sonnet")
        expected = (1000 / 1_000_000) * 3.00 + (500 / 1_000_000) * 15.00
        assert cost == pytest.approx(expected, rel=0.01)

    def test_unknown_model_defaults(self, estimator: TokenEstimator) -> None:
        """Unknown model defaults to GPT-4o pricing."""
        cost = estimator.estimate_cost(1000, 500, "unknown-model")
        assert cost > 0

    def test_zero_tokens(self, estimator: TokenEstimator) -> None:
        """Zero tokens costs zero."""
        cost = estimator.estimate_cost(0, 0)
        assert cost == 0.0


class TestModuleLevelFunctions:
    """Module-level convenience functions."""

    def test_estimate_tokens(self) -> None:
        """estimate_tokens uses default estimator."""
        tokens = estimate_tokens("Hello world")
        assert tokens > 0

    def test_estimate_tokens_with_language(self) -> None:
        """estimate_tokens with language parameter."""
        tokens = estimate_tokens("def foo(): pass", language="python")
        assert tokens > 0

    def test_estimate_file_tokens(self) -> None:
        """estimate_file_tokens uses default estimator."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write("print('test')\n")
            f.flush()
            f.close()
            tokens = estimate_file_tokens(f.name)
            Path(f.name).unlink()
            assert tokens > 0