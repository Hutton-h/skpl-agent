"""
Token Estimator — Estimates token counts for various content types.

Uses empirically-derived ratios based on common tokenizer behavior:
  - Code:     ~3.5 chars per token
  - Prose:    ~4.0 chars per token
  - Mixed:    ~3.75 chars per token

These ratios are calibrated against GPT-4 and Claude tokenizers.
When tiktoken is available, uses it for accurate counts.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Optional

# Try to use tiktoken for accurate counts
_HAS_TIKTOKEN = False
try:
    import tiktoken

    _HAS_TIKTOKEN = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Content Types
# ---------------------------------------------------------------------------


class ContentType(Enum):
    CODE = "code"
    PROSE = "prose"
    MIXED = "mixed"


# Chars-per-token ratios (empirically calibrated)
CHARS_PER_TOKEN: dict[ContentType, float] = {
    ContentType.CODE: 3.5,
    ContentType.PROSE: 4.0,
    ContentType.MIXED: 3.75,
}

# Language-specific ratios for more accurate estimation
LANGUAGE_RATIOS: dict[str, float] = {
    "python": 3.6,
    "typescript": 3.4,
    "javascript": 3.4,
    "go": 3.5,
    "rust": 3.3,
    "java": 3.2,
    "c": 3.6,
    "c++": 3.3,
    "c#": 3.3,
    "ruby": 3.8,
    "php": 3.5,
    "swift": 3.6,
    "kotlin": 3.4,
    "scala": 3.3,
    "lua": 3.9,
    "bash": 4.0,
    "sql": 4.0,
    "html": 4.2,
    "css": 3.8,
    "json": 3.5,
    "yaml": 4.0,
    "markdown": 4.0,
    "toml": 4.0,
    "xml": 3.8,
}


# ---------------------------------------------------------------------------
# Estimator
# ---------------------------------------------------------------------------


class TokenEstimator:
    """Estimate token counts for text content.

    When tiktoken is available, uses accurate tokenization.
    Otherwise falls back to character-ratio estimation.

    Usage:
        est = TokenEstimator()
        tokens = est.count(source_code, language="python")
        tokens = est.count_file("src/main.py")
    """

    # Default encoding for tiktoken
    DEFAULT_ENCODING = "cl100k_base"  # GPT-4 / GPT-3.5-turbo encoding

    def __init__(self, encoding_name: str | None = None):
        self.encoding_name = encoding_name or self.DEFAULT_ENCODING
        self._encoding = None
        if _HAS_TIKTOKEN:
            try:
                self._encoding = tiktoken.get_encoding(self.encoding_name)
            except Exception:
                pass

    def count(self, text: str, language: str | None = None) -> int:
        """Estimate token count for a text string."""
        if not text:
            return 0

        # Use tiktoken if available
        if self._encoding is not None:
            try:
                return len(self._encoding.encode(text))
            except Exception:
                pass

        # Fall back to character ratio estimation
        ratio = self._get_ratio(text, language)
        return max(1, int(len(text) / ratio))

    def count_file(self, file_path: str | Path) -> int:
        """Estimate token count for a file."""
        try:
            text = Path(file_path).read_text(encoding="utf-8", errors="replace")
            # Detect language from extension
            from skpl_agent.context.symbol_extractor import detect_language

            language = detect_language(file_path)
            return self.count(text, language)
        except Exception:
            return 0

    def count_batch(
        self, texts: list[str], language: str | None = None
    ) -> list[int]:
        """Estimate token counts for multiple texts."""
        return [self.count(text, language) for text in texts]

    def _get_ratio(self, text: str, language: str | None = None) -> float:
        """Determine the appropriate chars-per-token ratio."""
        # Use language-specific ratio if available
        if language and language in LANGUAGE_RATIOS:
            return LANGUAGE_RATIOS[language]

        # Detect content type from text characteristics
        content_type = self._detect_content_type(text)
        return CHARS_PER_TOKEN[content_type]

    @staticmethod
    def _detect_content_type(text: str) -> ContentType:
        """Detect whether text is code, prose, or mixed."""
        # Count code indicators
        code_indicators = len(
            re.findall(
                r"[{}();\[\]=<>+\-*/%&|^!~?:]|def\s|class\s|function\s|import\s|from\s|return\s|if\s|else\s|for\s|while\s",
                text,
            )
        )
        # Count prose indicators
        prose_indicators = len(re.findall(r"[.,;:!?]", text))
        # Count lines
        lines = text.count("\n") + 1
        # Average line length
        avg_line_len = len(text) / max(lines, 1)

        # Heuristic: code tends to have more brackets and shorter lines
        if code_indicators > prose_indicators * 2 and avg_line_len < 80:
            return ContentType.CODE
        elif prose_indicators > code_indicators * 2 and avg_line_len > 80:
            return ContentType.PROSE
        else:
            return ContentType.MIXED

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_name: str = "gpt-4o",
    ) -> float:
        """Estimate USD cost based on token counts and model pricing.

        Pricing is approximate and should be updated periodically.
        """
        # Approximate pricing per 1M tokens (as of mid-2026)
        PRICING: dict[str, dict[str, float]] = {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
            "claude-3-opus": {"input": 15.00, "output": 75.00},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        }

        model_pricing = PRICING.get(model_name, PRICING["gpt-4o"])
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        return round(input_cost + output_cost, 6)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_default_estimator = TokenEstimator()


def estimate_tokens(text: str, language: str | None = None) -> int:
    """Quick token count using the default estimator."""
    return _default_estimator.count(text, language)


def estimate_file_tokens(file_path: str | Path) -> int:
    """Quick token count for a file using the default estimator."""
    return _default_estimator.count_file(file_path)