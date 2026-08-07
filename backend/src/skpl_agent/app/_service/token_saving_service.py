"""Token Saving Service — A/B comparison of context-aware vs. baseline modes.

Provides quantitative measurement of token savings achieved by the SKPL
context management system.  Compares two modes:

1. **with_context**: Uses the full SKPL context pipeline (anatomy scan,
   symbol extraction, bug log, memory) to generate compact, targeted context
   for the LLM.

2. **without_context**: Baseline mode that sends raw file content or
   the full codebase as context without any filtering or compression.

The service computes savings rates, runs A/B comparison experiments,
and performs trend analysis over multiple runs.

Usage:
    >>> svc = TokenSavingService()
    >>> result = await svc.compare(
    ...     session_id="sess-1",
    ...     query="fix the bug in auth.py",
    ...     files=["src/auth.py", "src/models.py"],
    ... )
    >>> print(f"Saved {result['saving_rate']:.1%} tokens")
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from skpl_agent.context.token_estimator import TokenEstimator

logger = logging.getLogger(__name__)


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class ComparisonResult:
    """Result of a single A/B token usage comparison.

    Attributes:
        session_id: The session identifier.
        query: The query/prompt used for the comparison.
        files: List of files involved in the comparison.
        context_tokens: Token count when using SKPL context.
        baseline_tokens: Token count when using raw (baseline) mode.
        absolute_saving: Absolute number of tokens saved.
        saving_rate: Token saving rate as a fraction (0.0 to 1.0).
        mode: Comparison mode ("ab" for A/B test).
        timestamp: When the comparison was performed.
    """

    session_id: str
    query: str
    files: list[str]
    context_tokens: int
    baseline_tokens: int
    absolute_saving: int
    saving_rate: float
    mode: str = "ab"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TrendPoint:
    """A single data point in a saving rate trend.

    Attributes:
        timestamp: When the measurement was taken.
        saving_rate: The token saving rate at that point.
        context_tokens: Context-mode token count.
        baseline_tokens: Baseline-mode token count.
    """

    timestamp: datetime
    saving_rate: float
    context_tokens: int
    baseline_tokens: int


@dataclass
class TrendAnalysis:
    """Statistical analysis of a saving rate trend series.

    Attributes:
        points: The raw data points in the trend.
        mean_rate: Arithmetic mean of saving rates.
        median_rate: Median saving rate.
        min_rate: Minimum observed saving rate.
        max_rate: Maximum observed saving rate.
        std_dev: Standard deviation of saving rates.
        total_absolute_savings: Total tokens saved across all points.
        trend_direction: "improving", "stable", or "declining".
    """

    points: list[TrendPoint]
    mean_rate: float
    median_rate: float
    min_rate: float
    max_rate: float
    std_dev: float
    total_absolute_savings: int
    trend_direction: str  # "improving", "stable", "declining"


# ── Service ──────────────────────────────────────────────────────────────────


class TokenSavingService:
    """Service for measuring token savings from context management.

    Implements A/B comparison between context-aware (SKPL) and baseline
    (raw) modes.  Maintains a history of comparison results for trend
    analysis.

    The service uses TokenEstimator for accurate token counting and
    supports configurable baseline estimation strategies.
    """

    def __init__(
        self,
        encoding_name: str | None = None,
        max_history: int = 1000,
    ) -> None:
        """Initialize the token saving service.

        Args:
            encoding_name: tiktoken encoding name for token estimation.
                           Defaults to "cl100k_base" (GPT-4 encoding).
            max_history: Maximum number of historical comparison results
                         to retain for trend analysis.
        """
        self._estimator = TokenEstimator(encoding_name=encoding_name)
        self._max_history = max_history
        self._history: list[ComparisonResult] = []

    # ── A/B Comparison ───────────────────────────────────────────────────

    def with_context(
        self,
        session_id: str,
        query: str,
        context_text: str,
        files: list[str] | None = None,
    ) -> int:
        """Estimate token count when using SKPL context management.

        This represents the "A" side of the A/B comparison: the SKPL
        context management pipeline produces a compact, targeted context
        string that is sent to the LLM.

        Args:
            session_id: The session identifier.
            query: The user query/prompt.
            context_text: The context string produced by SKPL.
            files: Optional list of files involved.

        Returns:
            Estimated token count for the context+query combined.
        """
        combined = self._combine_prompt(query, context_text)
        tokens = self._estimator.count(combined)

        logger.debug(
            "with_context: session=%s query_len=%d context_len=%d tokens=%d",
            session_id,
            len(query),
            len(context_text),
            tokens,
        )
        return tokens

    def without_context(
        self,
        session_id: str,
        query: str,
        raw_content: str,
        files: list[str] | None = None,
    ) -> int:
        """Estimate token count when using raw (baseline) mode.

        This represents the "B" side of the A/B comparison: sending raw
        file content or the full codebase without any filtering, compression,
        or context management.

        Args:
            session_id: The session identifier.
            query: The user query/prompt.
            raw_content: The raw, uncompressed content that would be sent.
            files: Optional list of files involved.

        Returns:
            Estimated token count for the raw content+query combined.
        """
        combined = self._combine_prompt(query, raw_content)
        tokens = self._estimator.count(combined)

        logger.debug(
            "without_context: session=%s query_len=%d raw_len=%d tokens=%d",
            session_id,
            len(query),
            len(raw_content),
            tokens,
        )
        return tokens

    def compare(
        self,
        session_id: str,
        query: str,
        context_text: str = "",
        raw_content: str = "",
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a full A/B comparison between context and baseline modes.

        Computes token counts for both modes, calculates the absolute
        saving and saving rate, stores the result in history, and returns
        a summary dictionary.

        Args:
            session_id: The session identifier.
            query: The user query/prompt.
            context_text: The SKPL context string (A side).
            raw_content: The raw content string (B side).
            files: Optional list of files involved.

        Returns:
            A dictionary with the comparison results.
        """
        context_tokens = self.with_context(
            session_id=session_id,
            query=query,
            context_text=context_text,
            files=files,
        )
        baseline_tokens = self.without_context(
            session_id=session_id,
            query=query,
            raw_content=raw_content,
            files=files,
        )

        absolute_saving = max(0, baseline_tokens - context_tokens)
        saving_rate = self._compute_saving_rate(context_tokens, baseline_tokens)

        result = ComparisonResult(
            session_id=session_id,
            query=query,
            files=files or [],
            context_tokens=context_tokens,
            baseline_tokens=baseline_tokens,
            absolute_saving=absolute_saving,
            saving_rate=saving_rate,
        )

        self._add_to_history(result)

        logger.info(
            "A/B comparison: session=%s context=%d baseline=%d saved=%d rate=%.1f%%",
            session_id,
            context_tokens,
            baseline_tokens,
            absolute_saving,
            saving_rate * 100,
        )

        return {
            "session_id": result.session_id,
            "mode": result.mode,
            "context_tokens": result.context_tokens,
            "baseline_tokens": result.baseline_tokens,
            "absolute_saving": result.absolute_saving,
            "saving_rate": result.saving_rate,
            "saving_rate_pct": f"{result.saving_rate:.1%}",
            "files": result.files,
            "timestamp": result.timestamp.isoformat(),
        }

    # ── Saving Rate Calculations ─────────────────────────────────────────

    def saving_rate(self, session_id: str) -> float | None:
        """Get the most recent saving rate for a session.

        Args:
            session_id: The session identifier.

        Returns:
            The saving rate as a fraction (0.0 to 1.0), or None if no
            comparison has been performed for this session.
        """
        for result in reversed(self._history):
            if result.session_id == session_id:
                return result.saving_rate
        return None

    def average_saving_rate(self, session_id: str | None = None) -> float:
        """Compute the average saving rate across comparisons.

        Args:
            session_id: If provided, compute average only for this session.
                        If None, compute across all sessions.

        Returns:
            Average saving rate as a fraction (0.0 to 1.0).
        """
        results = self._filter_history(session_id)
        if not results:
            return 0.0
        return statistics.mean(r.saving_rate for r in results)

    def total_savings(self, session_id: str | None = None) -> int:
        """Total absolute tokens saved across all comparisons.

        Args:
            session_id: If provided, sum only for this session.

        Returns:
            Total absolute token savings.
        """
        results = self._filter_history(session_id)
        return sum(r.absolute_saving for r in results)

    # ── Trend Analysis ──────────────────────────────────────────────────

    def get_trend(self, session_id: str | None = None) -> TrendAnalysis:
        """Analyze the saving rate trend over time.

        Computes descriptive statistics (mean, median, min, max, std dev)
        and determines the trend direction (improving, stable, declining)
        based on recent movement.

        Args:
            session_id: If provided, analyze only this session's trend.

        Returns:
            A TrendAnalysis with statistical summary and direction.
        """
        results = self._filter_history(session_id)
        if not results:
            return TrendAnalysis(
                points=[],
                mean_rate=0.0,
                median_rate=0.0,
                min_rate=0.0,
                max_rate=0.0,
                std_dev=0.0,
                total_absolute_savings=0,
                trend_direction="stable",
            )

        points = [
            TrendPoint(
                timestamp=r.timestamp,
                saving_rate=r.saving_rate,
                context_tokens=r.context_tokens,
                baseline_tokens=r.baseline_tokens,
            )
            for r in results
        ]

        rates = [p.saving_rate for p in points]
        mean_rate = statistics.mean(rates)
        median_rate = statistics.median(rates)
        min_rate = min(rates)
        max_rate = max(rates)
        std_dev = statistics.stdev(rates) if len(rates) >= 2 else 0.0
        total_absolute = sum(p.baseline_tokens - p.context_tokens for p in points)

        trend_direction = self._classify_trend(rates)

        return TrendAnalysis(
            points=points,
            mean_rate=mean_rate,
            median_rate=median_rate,
            min_rate=min_rate,
            max_rate=max_rate,
            std_dev=std_dev,
            total_absolute_savings=total_absolute,
            trend_direction=trend_direction,
        )

    def get_trend_summary(self, session_id: str | None = None) -> dict[str, Any]:
        """Get a human-readable trend summary.

        Args:
            session_id: If provided, summarize only this session.

        Returns:
            A dictionary with trend statistics and interpretation.
        """
        trend = self.get_trend(session_id)
        return {
            "num_comparisons": len(trend.points),
            "mean_saving_rate": trend.mean_rate,
            "mean_saving_rate_pct": f"{trend.mean_rate:.1%}",
            "median_saving_rate": trend.median_rate,
            "median_saving_rate_pct": f"{trend.median_rate:.1%}",
            "min_saving_rate": trend.min_rate,
            "min_saving_rate_pct": f"{trend.min_rate:.1%}",
            "max_saving_rate": trend.max_rate,
            "max_saving_rate_pct": f"{trend.max_rate:.1%}",
            "std_dev": trend.std_dev,
            "total_absolute_savings": trend.total_absolute_savings,
            "trend_direction": trend.trend_direction,
        }

    # ── History Management ──────────────────────────────────────────────

    def get_history(self, session_id: str | None = None) -> list[dict[str, Any]]:
        """Get comparison history as a list of dictionaries.

        Args:
            session_id: If provided, filter to this session.

        Returns:
            List of comparison result dictionaries, most recent first.
        """
        results = self._filter_history(session_id)
        return [
            {
                "session_id": r.session_id,
                "context_tokens": r.context_tokens,
                "baseline_tokens": r.baseline_tokens,
                "absolute_saving": r.absolute_saving,
                "saving_rate": r.saving_rate,
                "saving_rate_pct": f"{r.saving_rate:.1%}",
                "query": r.query[:100],
                "files": r.files,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in reversed(results)
        ]

    def clear_history(self, session_id: str | None = None) -> int:
        """Clear comparison history.

        Args:
            session_id: If provided, clear only this session's history.

        Returns:
            Number of entries removed.
        """
        if session_id is None:
            count = len(self._history)
            self._history.clear()
            logger.info("Cleared all comparison history (%d entries)", count)
            return count

        before = len(self._history)
        self._history = [
            r for r in self._history if r.session_id != session_id
        ]
        after = len(self._history)
        removed = before - after
        logger.info(
            "Cleared comparison history for session=%s (%d entries)",
            session_id,
            removed,
        )
        return removed

    # ── Internal Helpers ────────────────────────────────────────────────

    def _combine_prompt(self, query: str, content: str) -> str:
        """Combine query and content into a single prompt string for counting."""
        return f"{query}\n\n{content}"

    @staticmethod
    def _compute_saving_rate(context_tokens: int, baseline_tokens: int) -> float:
        """Compute the token saving rate.

        Returns a value between 0.0 and 1.0. If baseline is 0, returns 0.0 to
        avoid division by zero.
        """
        if baseline_tokens <= 0:
            return 0.0
        if context_tokens >= baseline_tokens:
            return 0.0
        return (baseline_tokens - context_tokens) / baseline_tokens

    def _add_to_history(self, result: ComparisonResult) -> None:
        """Add a result to history, respecting max_history limit."""
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def _filter_history(self, session_id: str | None) -> list[ComparisonResult]:
        """Filter history by session_id. Returns all if session_id is None."""
        if session_id is None:
            return list(self._history)
        return [r for r in self._history if r.session_id == session_id]

    @staticmethod
    def _classify_trend(rates: list[float]) -> str:
        """Classify the trend direction from a series of saving rates.

        Uses linear regression on the last 10 points (or fewer if less data)
        to determine if the trend is improving, stable, or declining.

        A slope magnitude less than 0.01 is considered "stable".
        """
        if len(rates) < 2:
            return "stable"

        # Use last 10 points for trend classification
        recent = rates[-10:] if len(rates) >= 10 else rates
        n = len(recent)

        # Simple linear regression: y = mx + b
        x_mean = (n - 1) / 2.0
        y_mean = statistics.mean(recent)

        numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "declining"
        else:
            return "stable"