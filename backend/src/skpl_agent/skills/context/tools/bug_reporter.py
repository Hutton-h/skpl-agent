"""Bug reporter — track and manage bug reports.

Provides a lightweight bug tracking system for in-context bug
reporting, listing, and status management within the SKPL Agent.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

logger = logging.getLogger(__name__)


class BugSeverity(str, Enum):
    """Severity levels for bug reports."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"


class BugStatus(str, Enum):
    """Status values for bug tracking."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"
    CLOSED = "closed"


@dataclass
class BugRecord:
    """A single bug report record.

    Attributes:
        bug_id: Unique identifier for the bug.
        title: Short description of the bug.
        description: Detailed description of the bug.
        severity: Severity level.
        status: Current status of the bug.
        file_path: Path to the file where the bug was found.
        line_number: Line number where the bug was found.
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last update.
        tags: Optional tags for categorization.
        assigned_to: Optional assignee.
    """

    bug_id: str
    title: str
    description: str = ""
    severity: BugSeverity = BugSeverity.MEDIUM
    status: BugStatus = BugStatus.OPEN
    file_path: str = ""
    line_number: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    assigned_to: str = ""


class BugReporter:
    """Lightweight bug tracking and reporting tool.

    Manages bug reports with CRUD operations and status tracking.
    Stores bugs in memory; suitable for per-session bug tracking.

    Usage:
        >>> reporter = BugReporter()
        >>> bug = reporter.report_bug(
        ...     title="Null pointer in parser",
        ...     description="Parser crashes on empty input",
        ...     severity=BugSeverity.HIGH,
        ...     file_path="src/parser.py",
        ...     line_number=42,
        ... )
        >>> bugs = reporter.list_bugs(status_filter=BugStatus.OPEN)
        >>> reporter.update_bug_status(bug.bug_id, BugStatus.RESOLVED)
    """

    def __init__(self) -> None:
        self._bugs: dict[str, BugRecord] = {}

    # ── Main API ─────────────────────────────────────────────────────────

    def report_bug(
        self,
        title: str,
        description: str = "",
        severity: BugSeverity | str = BugSeverity.MEDIUM,
        file_path: str = "",
        line_number: int = 0,
        tags: list[str] | None = None,
        assigned_to: str = "",
    ) -> BugRecord:
        """Create a new bug report.

        Args:
            title: Short description of the bug.
            description: Detailed description of the bug.
            severity: Severity level (BugSeverity enum or string).
            file_path: Path to the file where the bug was found.
            line_number: Line number where the bug was found.
            tags: Optional list of tags for categorization.
            assigned_to: Optional assignee identifier.

        Returns:
            The created BugRecord.
        """
        if isinstance(severity, str):
            severity = BugSeverity(severity)

        bug_id = str(uuid.uuid4())[:8]
        now = time.time()

        bug = BugRecord(
            bug_id=bug_id,
            title=title,
            description=description,
            severity=severity,
            status=BugStatus.OPEN,
            file_path=file_path,
            line_number=line_number,
            created_at=now,
            updated_at=now,
            tags=tags or [],
            assigned_to=assigned_to,
        )

        self._bugs[bug_id] = bug
        logger.info(
            "Bug reported: [%s] %s (severity=%s, file=%s:%d)",
            bug_id, title, severity.value, file_path, line_number,
        )
        return bug

    def list_bugs(
        self,
        status_filter: BugStatus | str | None = None,
        severity_filter: BugSeverity | str | None = None,
        sort_by: Literal["created_at", "severity", "updated_at"] = "created_at",
    ) -> list[BugRecord]:
        """List bugs with optional filtering.

        Args:
            status_filter: Filter by bug status. None returns all statuses.
            severity_filter: Filter by severity. None returns all severities.
            sort_by: Sort order for results.

        Returns:
            Filtered and sorted list of BugRecord objects.
        """
        bugs = list(self._bugs.values())

        if status_filter is not None:
            if isinstance(status_filter, str):
                status_filter = BugStatus(status_filter)
            bugs = [b for b in bugs if b.status == status_filter]

        if severity_filter is not None:
            if isinstance(severity_filter, str):
                severity_filter = BugSeverity(severity_filter)
            bugs = [b for b in bugs if b.severity == severity_filter]

        # Sort
        severity_order = {
            BugSeverity.CRITICAL: 0,
            BugSeverity.HIGH: 1,
            BugSeverity.MEDIUM: 2,
            BugSeverity.LOW: 3,
            BugSeverity.TRIVIAL: 4,
        }

        if sort_by == "severity":
            bugs.sort(key=lambda b: severity_order.get(b.severity, 99))
        elif sort_by == "updated_at":
            bugs.sort(key=lambda b: b.updated_at, reverse=True)
        else:
            bugs.sort(key=lambda b: b.created_at, reverse=True)

        logger.debug("Listed %d bugs (filter: status=%s, severity=%s)",
                      len(bugs), status_filter, severity_filter)
        return bugs

    def update_bug_status(
        self, bug_id: str, new_status: BugStatus | str,
    ) -> Optional[BugRecord]:
        """Update the status of an existing bug.

        Args:
            bug_id: The unique identifier of the bug.
            new_status: The new status to set.

        Returns:
            The updated BugRecord, or None if the bug_id was not found.
        """
        if bug_id not in self._bugs:
            logger.warning("Bug not found: %s", bug_id)
            return None

        if isinstance(new_status, str):
            new_status = BugStatus(new_status)

        bug = self._bugs[bug_id]
        old_status = bug.status
        bug.status = new_status
        bug.updated_at = time.time()

        logger.info(
            "Bug [%s] status: %s -> %s", bug_id, old_status.value, new_status.value,
        )
        return bug

    def get_bug(self, bug_id: str) -> Optional[BugRecord]:
        """Get a single bug by its ID.

        Args:
            bug_id: The unique identifier of the bug.

        Returns:
            The BugRecord if found, None otherwise.
        """
        return self._bugs.get(bug_id)

    def update_bug(
        self,
        bug_id: str,
        title: str | None = None,
        description: str | None = None,
        severity: BugSeverity | str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
        tags: list[str] | None = None,
        assigned_to: str | None = None,
    ) -> Optional[BugRecord]:
        """Update fields of an existing bug.

        Args:
            bug_id: The unique identifier of the bug.
            title: New title (None to leave unchanged).
            description: New description (None to leave unchanged).
            severity: New severity (None to leave unchanged).
            file_path: New file path (None to leave unchanged).
            line_number: New line number (None to leave unchanged).
            tags: New tags (None to leave unchanged).
            assigned_to: New assignee (None to leave unchanged).

        Returns:
            The updated BugRecord, or None if the bug_id was not found.
        """
        bug = self._bugs.get(bug_id)
        if bug is None:
            logger.warning("Bug not found for update: %s", bug_id)
            return None

        if title is not None:
            bug.title = title
        if description is not None:
            bug.description = description
        if severity is not None:
            if isinstance(severity, str):
                severity = BugSeverity(severity)
            bug.severity = severity
        if file_path is not None:
            bug.file_path = file_path
        if line_number is not None:
            bug.line_number = line_number
        if tags is not None:
            bug.tags = tags
        if assigned_to is not None:
            bug.assigned_to = assigned_to

        bug.updated_at = time.time()
        logger.info("Bug [%s] updated", bug_id)
        return bug

    def delete_bug(self, bug_id: str) -> bool:
        """Delete a bug by its ID.

        Args:
            bug_id: The unique identifier of the bug to delete.

        Returns:
            True if deleted, False if not found.
        """
        if bug_id in self._bugs:
            del self._bugs[bug_id]
            logger.info("Bug [%s] deleted", bug_id)
            return True
        logger.warning("Bug not found for deletion: %s", bug_id)
        return False

    @property
    def total_bugs(self) -> int:
        """Total number of bugs in the tracker."""
        return len(self._bugs)

    def summarize(self) -> dict[str, int]:
        """Get a summary of bug counts by status.

        Returns:
            Dictionary mapping status value to count.
        """
        summary: dict[str, int] = {}
        for bug in self._bugs.values():
            key = bug.status.value
            summary[key] = summary.get(key, 0) + 1
        return summary