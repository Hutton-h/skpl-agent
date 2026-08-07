"""
Waste Detector — Identifies wasteful token usage patterns.

Detects common patterns that waste tokens:
1. Repeated file reads (same file read multiple times)
2. Redundant context injection (unchanged context re-sent)
3. Overly large context windows
4. Duplicate tool outputs

Based on OpenWolf's token waste analysis algorithms.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Waste Patterns
# ---------------------------------------------------------------------------


@dataclass
class WastePattern:
    """A detected waste pattern."""

    pattern_type: str  # duplicate_read, redundant_context, oversized_context, duplicate_output
    severity: str  # low, medium, high
    description: str
    tokens_wasted: int
    file_path: str | None = None
    context_hash: str | None = None
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class WasteDetector:
    """Detects and reports wasteful token usage patterns.

    Usage:
        detector = WasteDetector()
        detector.record_file_read("src/main.py", 500)
        if detector.is_wasteful_read("src/main.py"):
            print("This file was already read, skipping re-injection")
    """

    def __init__(
        self,
        duplicate_read_threshold: int = 1,  # Flag after N+1 reads
        context_hashing_enabled: bool = True,
        max_file_reads: int = 5,
    ):
        self.duplicate_read_threshold = duplicate_read_threshold
        self.context_hashing_enabled = context_hashing_enabled
        self.max_file_reads = max_file_reads

        # Tracking state
        self._file_read_counts: dict[str, int] = defaultdict(int)
        self._file_last_hash: dict[str, str] = {}
        self._context_history: dict[str, list[str]] = defaultdict(list)
        self._output_history: dict[str, list[str]] = defaultdict(list)
        self._detected_patterns: list[WastePattern] = []

    # -- File Read Tracking --

    def record_file_read(self, file_path: str, token_count: int = 0) -> None:
        """Record that a file was read."""
        self._file_read_counts[file_path] += 1

        if self._file_read_counts[file_path] > self.duplicate_read_threshold + 1:
            self._detected_patterns.append(
                WastePattern(
                    pattern_type="duplicate_read",
                    severity="medium",
                    description=f"File '{file_path}' read {self._file_read_counts[file_path]} times",
                    tokens_wasted=token_count * (self._file_read_counts[file_path] - 1),
                    file_path=file_path,
                )
            )

    def is_wasteful_read(self, file_path: str) -> bool:
        """Check if reading this file again would be wasteful."""
        return self._file_read_counts[file_path] > self.max_file_reads

    def get_read_count(self, file_path: str) -> int:
        return self._file_read_counts.get(file_path, 0)

    # -- Context Tracking --

    def record_context_injection(self, session_id: str, context: str) -> bool:
        """Record a context injection. Returns True if context is unchanged.

        When context is unchanged, the caller should skip re-injection
        to save tokens.
        """
        if not self.context_hashing_enabled:
            return False

        context_hash = self._hash_content(context)
        self._context_history[session_id].append(context_hash)

        if len(self._context_history[session_id]) >= 2:
            if self._context_history[session_id][-1] == self._context_history[session_id][-2]:
                self._detected_patterns.append(
                    WastePattern(
                        pattern_type="redundant_context",
                        severity="low",
                        description="Context unchanged from previous injection",
                        tokens_wasted=len(context) // 4,  # rough token estimate
                        context_hash=context_hash,
                    )
                )
                return True

        return False

    # -- Output Tracking --

    def record_tool_output(self, tool_name: str, output: str) -> bool:
        """Record a tool output. Returns True if output is duplicate."""
        output_hash = self._hash_content(output)
        self._output_history[tool_name].append(output_hash)

        # Check last 5 outputs for duplicates
        recent = self._output_history[tool_name][-6:-1]  # exclude current
        if output_hash in recent:
            self._detected_patterns.append(
                WastePattern(
                    pattern_type="duplicate_output",
                    severity="medium",
                    description=f"Tool '{tool_name}' produced duplicate output",
                    tokens_wasted=len(output) // 4,
                )
            )
            return True

        return False

    # -- Oversized Context Detection --

    def check_context_size(self, context: str, max_tokens: int = 100000) -> Optional[WastePattern]:
        """Check if context is oversized."""
        estimated_tokens = len(context) // 4
        if estimated_tokens > max_tokens:
            pattern = WastePattern(
                pattern_type="oversized_context",
                severity="high",
                description=f"Context size ({estimated_tokens} tokens) exceeds limit ({max_tokens})",
                tokens_wasted=estimated_tokens - max_tokens,
            )
            self._detected_patterns.append(pattern)
            return pattern
        return None

    # -- Results --

    def get_patterns(self) -> list[WastePattern]:
        """Get all detected waste patterns."""
        return list(self._detected_patterns)

    def get_total_waste(self) -> int:
        """Get total tokens wasted across all patterns."""
        return sum(p.tokens_wasted for p in self._detected_patterns)

    def get_waste_summary(self) -> dict:
        """Get a summary of waste by type."""
        summary: dict[str, int] = {}
        for pattern in self._detected_patterns:
            summary[pattern.pattern_type] = (
                summary.get(pattern.pattern_type, 0) + pattern.tokens_wasted
            )
        return summary

    def reset(self) -> None:
        """Reset all tracking state."""
        self._file_read_counts.clear()
        self._file_last_hash.clear()
        self._context_history.clear()
        self._output_history.clear()
        self._detected_patterns.clear()

    # -- Helpers --

    @staticmethod
    def _hash_content(content: str) -> str:
        """Hash content for comparison."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()