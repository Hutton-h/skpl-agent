"""Token analyzer — estimate and analyze token usage in messages.

Provides token counting, message analysis, and waste detection
for LLM context windows. Uses a character-based heuristic by default
with optional tiktoken integration for more accurate counts.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tokenizer Protocol
# ---------------------------------------------------------------------------

class Tokenizer(Protocol):
    """Protocol for pluggable tokenizer implementations."""

    def encode(self, text: str) -> list[int]:
        """Encode text into token IDs."""
        ...

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs back to text."""
        ...


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class MessageAnalysis:
    """Analysis result for a single message.

    Attributes:
        index: Position of the message in the conversation.
        role: The role of the message (user, assistant, system).
        content_length: Character count of the message content.
        estimated_tokens: Estimated token count.
        is_waste: Whether this message is flagged as wasteful.
        waste_reason: Reason for waste flag, if applicable.
    """

    index: int
    role: str = "user"
    content_length: int = 0
    estimated_tokens: int = 0
    is_waste: bool = False
    waste_reason: str = ""


@dataclass
class TokenUsageReport:
    """Complete token usage analysis report.

    Attributes:
        total_tokens: Total estimated tokens across all messages.
        message_count: Number of messages analyzed.
        message_analyses: Per-message analysis results.
        wasted_tokens: Estimated tokens wasted.
        waste_percentage: Fraction of total tokens identified as waste.
        efficiency_score: 0-100 score indicating token efficiency.
        recommendations: List of recommendations to reduce waste.
        duration_ms: Analysis time in milliseconds.
        error: Error message if analysis failed.
    """

    total_tokens: int = 0
    message_count: int = 0
    message_analyses: list[MessageAnalysis] = field(default_factory=list)
    wasted_tokens: int = 0
    waste_percentage: float = 0.0
    efficiency_score: float = 100.0
    recommendations: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str = ""


# ---------------------------------------------------------------------------
# Waste Detection Patterns
# ---------------------------------------------------------------------------

_WASTE_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, reason)
    (r"(?i)(as an AI|as a language model|I am an AI)", "AI identity boilerplate"),
    (r"(?i)(if you have (any|more) questions|feel free to ask|let me know if you need)", "Overly polite closing"),
    (r"(?i)(I hope this (message|email|response) finds you well)", "Email pleasantry"),
    (r"(?i)(please note that|it is important to note that|I would like to point out)", "Hedging phrase"),
    (r"(?i)(in conclusion|to summarize|in summary)", "Redundant summary start"),
    (r"(?i)(^\s*(ok|okay|sure|got it|understood)\s*$)", "Minimal acknowledgment"),
    (r"^(\s|\n)*$", "Empty or whitespace-only message"),
]

# Minimum token threshold for waste detection (short messages are not wasteful)
_WASTE_MIN_TOKENS = 10


class TokenAnalyzer:
    """Estimates and analyzes token usage in LLM conversations.

    Provides character-based token estimation (4 chars ~= 1 token)
    with optional tiktoken integration for precise counts. Includes
    waste detection to identify inefficient token usage patterns.

    Usage:
        >>> analyzer = TokenAnalyzer()
        >>> tokens = analyzer.estimate_tokens("Hello, world!")
        >>> print(f"~{tokens} tokens")
        >>> messages = [
        ...     {"role": "user", "content": "What is Python?"},
        ...     {"role": "assistant", "content": "Python is a programming language..."},
        ... ]
        >>> report = analyzer.analyze_message(messages)
        >>> print(f"Total: {report.total_tokens}, Waste: {report.waste_percentage:.1%}")
    """

    # Default ratio: ~4 characters per token for English text
    _DEFAULT_CHARS_PER_TOKEN = 4.0

    def __init__(self, tokenizer: Tokenizer | None = None) -> None:
        """Initialize the token analyzer.

        Args:
            tokenizer: Optional custom tokenizer implementing the Tokenizer
                       protocol. If not provided, character-based estimation
                       is used. Pass a tiktoken encoding for precise counts.
        """
        self._tokenizer = tokenizer

    # ── Main API ─────────────────────────────────────────────────────────

    def estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a text.

        Uses the configured tokenizer if available, otherwise falls
        back to character-based estimation (default: 4 chars/token).

        Args:
            text: The text to estimate token count for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0

        if self._tokenizer is not None:
            try:
                return len(self._tokenizer.encode(text))
            except Exception as e:
                logger.warning("Tokenizer encode failed, falling back to estimate: %s", e)

        # Character-based estimation
        return max(1, math.ceil(len(text) / self._DEFAULT_CHARS_PER_TOKEN))

    def analyze_message(
        self,
        messages: list[dict[str, Any]],
        detect_waste: bool = True,
        waste_threshold_pct: float = 0.3,
    ) -> TokenUsageReport:
        """Analyze token usage across a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            detect_waste: Whether to run waste detection.
            waste_threshold_pct: Fraction of total tokens that, if exceeded
                                 by waste, flags the conversation.

        Returns:
            TokenUsageReport with per-message analysis and recommendations.
        """
        import re
        import time

        start = time.monotonic()

        if not messages:
            return TokenUsageReport(
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            analyses: list[MessageAnalysis] = []
            total_tokens = 0
            wasted_tokens = 0

            for idx, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = str(msg.get("content", ""))
                char_len = len(content)
                tokens = self.estimate_tokens(content)

                analysis = MessageAnalysis(
                    index=idx,
                    role=role,
                    content_length=char_len,
                    estimated_tokens=tokens,
                )

                if detect_waste and tokens >= _WASTE_MIN_TOKENS:
                    is_waste, reason = self._check_waste(content)
                    analysis.is_waste = is_waste
                    analysis.waste_reason = reason
                    if is_waste:
                        wasted_tokens += tokens

                analyses.append(analysis)
                total_tokens += tokens

            # Calculate efficiency
            waste_pct = wasted_tokens / max(total_tokens, 1)
            efficiency = max(0.0, 100.0 * (1.0 - waste_pct))

            # Generate recommendations
            recommendations = self._generate_recommendations(
                analyses, waste_pct, waste_threshold_pct,
            )

            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "Analyzed %d messages: %d tokens, %.1f%% waste, efficiency=%.1f",
                len(messages), total_tokens, waste_pct * 100, efficiency,
            )

            return TokenUsageReport(
                total_tokens=total_tokens,
                message_count=len(messages),
                message_analyses=analyses,
                wasted_tokens=wasted_tokens,
                waste_percentage=round(waste_pct, 4),
                efficiency_score=round(efficiency, 1),
                recommendations=recommendations,
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error("Message analysis error: %s", e)
            return TokenUsageReport(
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    def detect_waste(
        self,
        messages: list[dict[str, Any]],
    ) -> list[MessageAnalysis]:
        """Detect wasteful patterns in a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            List of MessageAnalysis objects flagged as waste.
        """
        report = self.analyze_message(messages, detect_waste=True)
        return [a for a in report.message_analyses if a.is_waste]

    # ── Waste Detection ──────────────────────────────────────────────────

    @staticmethod
    def _check_waste(content: str) -> tuple[bool, str]:
        """Check a single message for waste patterns.

        Args:
            content: The message content to check.

        Returns:
            Tuple of (is_waste, reason).
        """
        import re

        for pattern, reason in _WASTE_PATTERNS:
            if re.search(pattern, content):
                return True, reason

        return False, ""

    # ── Recommendations ──────────────────────────────────────────────────

    @staticmethod
    def _generate_recommendations(
        analyses: list[MessageAnalysis],
        waste_pct: float,
        threshold: float,
    ) -> list[str]:
        """Generate recommendations based on analysis results.

        Args:
            analyses: Per-message analysis results.
            waste_pct: Overall waste percentage.
            threshold: Waste threshold for flagging.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        if waste_pct > threshold:
            recommendations.append(
                f"High token waste detected ({waste_pct:.1%}). Consider trimming "
                "redundant content, boilerplate, and pleasantries."
            )

        # Count waste by type
        waste_counts: dict[str, int] = {}
        for a in analyses:
            if a.is_waste and a.waste_reason:
                waste_counts[a.waste_reason] = waste_counts.get(a.waste_reason, 0) + 1

        if waste_counts:
            top_waste = sorted(waste_counts.items(), key=lambda x: -x[1])[:3]
            for reason, count in top_waste:
                recommendations.append(
                    f"Found {count} instance(s) of '{reason}'. "
                    "Remove or reduce these patterns."
                )

        # Check for long messages
        long_messages = [a for a in analyses if a.estimated_tokens > 2000]
        if long_messages:
            recommendations.append(
                f"Found {len(long_messages)} message(s) exceeding 2000 tokens. "
                "Consider splitting into smaller chunks."
            )

        # Check for excessive system messages
        system_messages = [a for a in analyses if a.role == "system"]
        if len(system_messages) > 3:
            recommendations.append(
                f"Found {len(system_messages)} system messages. "
                "Consider consolidating into fewer system prompts."
            )

        if not recommendations:
            recommendations.append("Token usage appears efficient. No changes recommended.")

        return recommendations

    # ── Utility ──────────────────────────────────────────────────────────

    @classmethod
    def with_tiktoken(cls, model: str = "gpt-4") -> TokenAnalyzer:
        """Create a TokenAnalyzer with tiktoken for precise counting.

        Args:
            model: The model name for tiktoken encoding selection.

        Returns:
            TokenAnalyzer instance configured with tiktoken.

        Raises:
            ImportError: If tiktoken is not installed.
        """
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(model)
            return cls(tokenizer=encoding)
        except ImportError:
            logger.warning(
                "tiktoken not installed. Falling back to character-based estimation. "
                "Install with: pip install tiktoken"
            )
            return cls()

    def estimate_cost(
        self,
        messages: list[dict[str, Any]],
        input_price_per_1k: float = 0.01,
        output_price_per_1k: float = 0.03,
    ) -> dict[str, float]:
        """Estimate API cost for a conversation.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            input_price_per_1k: Price per 1000 input tokens.
            output_price_per_1k: Price per 1000 output tokens.

        Returns:
            Dictionary with input_tokens, output_tokens, estimated_cost_usd.
        """
        input_tokens = 0
        output_tokens = 0

        for msg in messages:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            tokens = self.estimate_tokens(content)

            if role == "assistant":
                output_tokens += tokens
            else:
                input_tokens += tokens

        input_cost = (input_tokens / 1000) * input_price_per_1k
        output_cost = (output_tokens / 1000) * output_price_per_1k

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": round(input_cost + output_cost, 6),
        }