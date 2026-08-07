"""
Bug Matcher — Jaccard similarity-based bug deduplication.

Computes fingerprints for bug records and finds duplicates using
a combination of exact fingerprint matching and fuzzy error message
similarity. This prevents the same bug from being logged multiple
times and helps agents learn from past failures more efficiently.

Based on OpenWolf's bug deduplication algorithm.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional


class BugMatcher:
    """Matches bugs to detect duplicates using fingerprinting and similarity.

    Usage:
        matcher = BugMatcher()
        fp = matcher.compute_fingerprint(
            error_type="SyntaxError",
            error_message="invalid syntax at line 42",
            file_path="src/main.py",
            line_number=42,
        )
        dup = matcher.find_duplicate(fp, error_message, existing_bugs)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        normalize_messages: bool = True,
    ):
        self.similarity_threshold = similarity_threshold
        self.normalize_messages = normalize_messages

    def compute_fingerprint(
        self,
        error_type: str,
        error_message: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> str:
        """Compute a unique fingerprint for a bug.

        The fingerprint is based on error type + normalized message.
        File path and line number are excluded to allow matching
        across different locations.
        """
        normalized = self._normalize_message(error_message) if self.normalize_messages else error_message
        key = f"{error_type}:{normalized}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:64]

    def find_duplicate(
        self,
        fingerprint: str,
        error_message: str,
        existing_bugs: list,
        max_check: int = 100,
    ) -> Optional[str]:
        """Find a duplicate bug among existing bugs.

        Returns the ID of the duplicate if found, None otherwise.
        """
        if not existing_bugs:
            return None

        # Check exact fingerprint match first (fast path)
        for bug in existing_bugs[-max_check:]:
            if hasattr(bug, "fingerprint") and bug.fingerprint == fingerprint:
                return bug.id

        # Fuzzy message similarity (slower fallback)
        normalized = self._normalize_message(error_message)
        for bug in existing_bugs[-max_check:]:
            if hasattr(bug, "error_message"):
                existing_msg = self._normalize_message(bug.error_message)
                similarity = self._jaccard_similarity(normalized, existing_msg)
                if similarity >= self.similarity_threshold:
                    return bug.id

        return None

    def _normalize_message(self, message: str) -> str:
        """Normalize an error message for comparison.

        Removes variable parts like line numbers, file paths, memory
        addresses, timestamps, and UUIDs to make messages comparable.
        """
        # Remove line numbers
        message = re.sub(r"line \d+", "line N", message, flags=re.IGNORECASE)
        message = re.sub(r"at line \d+", "at line N", message, flags=re.IGNORECASE)

        # Remove file paths (common patterns) — BEFORE :\d+:\d+ to avoid mangling paths
        message = re.sub(r'["\']?[\w./\\-]+\.(?:py|ts|js|go|rs|java|rb|php|cpp|c|h|hpp|swift|kt)["\']?', "[FILE]", message)
        message = re.sub(r"File\s+[\"'][^\"']+[\"']", "File [PATH]", message)

        # Remove memory addresses
        message = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", message)
        message = re.sub(r"at 0x[0-9a-fA-F]+", "at 0xADDR", message)

        # Remove timestamps — BEFORE :\d+:\d+ to avoid mangling time portions
        message = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?", "[TIMESTAMP]", message)

        # Remove UUIDs
        message = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "[UUID]", message, flags=re.IGNORECASE)

        # Remove hex IDs
        message = re.sub(r"\b[0-9a-f]{32,}\b", "[HEXID]", message, flags=re.IGNORECASE)

        # Remove generic :\d+:\d+ patterns (line:column notation)
        message = re.sub(r":\d+:\d+", ":N:N", message)

        # Remove numbers (standalone, not part of words)
        message = re.sub(r"\b\d+\b", "N", message)

        # Collapse whitespace
        message = re.sub(r"\s+", " ", message).strip().lower()

        return message

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity between two strings.

        Jaccard = |intersection| / |union| of word sets.
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        # Tokenize into words
        words1 = set(text1.split())
        words2 = set(text2.split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        return intersection / union

    def find_similar(
        self,
        error_message: str,
        existing_bugs: list,
        min_similarity: float = 0.6,
        limit: int = 5,
    ) -> list[tuple[str, float]]:
        """Find similar bugs, returning (bug_id, similarity) pairs."""
        normalized = self._normalize_message(error_message)
        results: list[tuple[str, float]] = []

        for bug in existing_bugs:
            if hasattr(bug, "error_message"):
                existing_msg = self._normalize_message(bug.error_message)
                similarity = self._jaccard_similarity(normalized, existing_msg)
                if similarity >= min_similarity:
                    results.append((bug.id, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]