"""
BugLog — Records and manages bugs encountered during agent execution.

Provides CRUD operations for bug records, enabling agents to learn
from past failures. Integrates with the `skpl_buglogs` database table
and the bug matcher for deduplication.

Based on OpenWolf's bug tracking system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


class BugStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


@dataclass
class BugRecord:
    """A single bug encountered during agent execution."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    agent_id: str | None = None
    error_type: str = ""
    error_message: str = ""
    error_traceback: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    context_snippet: str | None = None
    fingerprint: str = ""  # unique hash for deduplication
    duplicate_of: str | None = None
    status: str = BugStatus.OPEN.value
    resolution: str | None = None
    resolved_at: datetime | None = None
    metadata_json: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# BugLog Manager
# ---------------------------------------------------------------------------


class BugLog:
    """In-memory bug log with optional persistence.

    Usage:
        buglog = BugLog(session_id="sess-123")
        buglog.log(
            error_type="SyntaxError",
            error_message="invalid syntax at line 42",
            error_traceback=traceback_str,
            file_path="src/main.py",
            line_number=42,
        )
        recent = buglog.get_recent(limit=10)
    """

    def __init__(self, session_id: str = "", max_entries: int = 1000):
        self.session_id = session_id
        self.max_entries = max_entries
        self._bugs: dict[str, BugRecord] = {}
        self._bug_matcher = None  # lazy import to avoid circular deps

    # -- Logging --

    def log(
        self,
        error_type: str,
        error_message: str,
        error_traceback: str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
        context_snippet: str | None = None,
        agent_id: str | None = None,
        metadata: dict | None = None,
    ) -> BugRecord:
        """Log a new bug."""
        import json

        from skpl_agent.context.bug_matcher import BugMatcher

        if self._bug_matcher is None:
            self._bug_matcher = BugMatcher()

        # Generate fingerprint
        fingerprint = self._bug_matcher.compute_fingerprint(
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
        )

        # Check for duplicates
        duplicate_id = self._bug_matcher.find_duplicate(
            fingerprint=fingerprint,
            error_message=error_message,
            existing_bugs=list(self._bugs.values()),
        )

        bug = BugRecord(
            session_id=self.session_id,
            agent_id=agent_id,
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
            file_path=file_path,
            line_number=line_number,
            context_snippet=context_snippet,
            fingerprint=fingerprint,
            duplicate_of=duplicate_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        if duplicate_id:
            bug.status = BugStatus.DUPLICATE.value

        self._bugs[bug.id] = bug

        # Trim if over max
        if len(self._bugs) > self.max_entries:
            # Remove oldest entries
            sorted_bugs = sorted(
                self._bugs.values(), key=lambda b: b.created_at
            )
            for old_bug in sorted_bugs[: len(self._bugs) - self.max_entries]:
                del self._bugs[old_bug.id]

        return bug

    def log_exception(
        self,
        exc: Exception,
        file_path: str | None = None,
        line_number: int | None = None,
        agent_id: str | None = None,
    ) -> BugRecord:
        """Log a bug from an exception object."""
        import traceback

        return self.log(
            error_type=type(exc).__name__,
            error_message=str(exc),
            error_traceback=traceback.format_exc(),
            file_path=file_path,
            line_number=line_number,
            agent_id=agent_id,
        )

    # -- Queries --

    def get(self, bug_id: str) -> BugRecord | None:
        """Get a bug by ID."""
        return self._bugs.get(bug_id)

    def get_recent(self, limit: int = 10) -> list[BugRecord]:
        """Get the most recent bugs."""
        return sorted(
            self._bugs.values(), key=lambda b: b.created_at, reverse=True
        )[:limit]

    def get_by_type(self, error_type: str) -> list[BugRecord]:
        """Get bugs by error type."""
        return [b for b in self._bugs.values() if b.error_type == error_type]

    def get_by_file(self, file_path: str) -> list[BugRecord]:
        """Get bugs associated with a file."""
        return [b for b in self._bugs.values() if b.file_path == file_path]

    def get_by_session(self, session_id: str) -> list[BugRecord]:
        """Get bugs for a specific session."""
        return [b for b in self._bugs.values() if b.session_id == session_id]

    def get_open(self) -> list[BugRecord]:
        """Get all open (unresolved) bugs."""
        return [b for b in self._bugs.values() if b.status == BugStatus.OPEN.value]

    # -- Updates --

    def update_status(
        self, bug_id: str, status: BugStatus, resolution: str | None = None
    ) -> BugRecord | None:
        """Update bug status."""
        bug = self._bugs.get(bug_id)
        if bug is None:
            return None

        bug.status = status.value
        bug.updated_at = datetime.now(timezone.utc)

        if resolution:
            bug.resolution = resolution

        if status in (BugStatus.RESOLVED, BugStatus.WONT_FIX, BugStatus.DUPLICATE):
            bug.resolved_at = datetime.now(timezone.utc)

        return bug

    def mark_duplicate(self, bug_id: str, duplicate_of: str) -> BugRecord | None:
        """Mark a bug as a duplicate of another."""
        bug = self._bugs.get(bug_id)
        if bug is None:
            return None

        bug.duplicate_of = duplicate_of
        bug.status = BugStatus.DUPLICATE.value
        bug.updated_at = datetime.now(timezone.utc)
        bug.resolved_at = datetime.now(timezone.utc)
        return bug

    # -- Stats --

    def get_stats(self) -> dict:
        """Get bug statistics."""
        total = len(self._bugs)
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        duplicates = 0

        for bug in self._bugs.values():
            by_type[bug.error_type] = by_type.get(bug.error_type, 0) + 1
            by_status[bug.status] = by_status.get(bug.status, 0) + 1
            if bug.duplicate_of:
                duplicates += 1

        return {
            "total": total,
            "open": by_status.get("open", 0),
            "resolved": by_status.get("resolved", 0),
            "duplicates": duplicates,
            "by_type": by_type,
            "by_status": by_status,
        }

    def clear(self) -> None:
        """Clear all bugs."""
        self._bugs.clear()

    def get_all(self) -> list[BugRecord]:
        """Get all bugs."""
        return list(self._bugs.values())