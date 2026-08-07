"""SKPL Agent custom event definitions for context management.

Extends AgentScope's CustomEvent mechanism with well-known event names
for the SKPL context subsystem. These events are dispatched through
AgentScope's event bus and consumed by the frontend for real-time
updates on context operations.

All events use the CustomEvent type with a ``name`` discriminator.
Frontend consumers should handle unknown names gracefully.
"""

from __future__ import annotations

from enum import Enum


class SKPLContextEventName(str, Enum):
    """Well-known event names for SKPL context management.

    These names are used as the ``name`` field of AgentScope's
    :class:`~agentscope.event.CustomEvent` to identify SKPL-specific
    signals.
    """

    # Session lifecycle
    CONTEXT_SESSION_STARTED = "context:session_started"
    """A new context session has been initialized."""

    CONTEXT_SESSION_ENDED = "context:session_ended"
    """A context session has been shut down."""

    # Anatomy
    ANATOMY_SCAN_STARTED = "context:anatomy_scan_started"
    """An anatomy scan has begun."""

    ANATOMY_SCAN_PROGRESS = "context:anatomy_scan_progress"
    """Anatomy scan progress update (includes file count, current file)."""

    ANATOMY_SCAN_COMPLETED = "context:anatomy_scan_completed"
    """An anatomy scan has finished successfully."""

    ANATOMY_SCAN_FAILED = "context:anatomy_scan_failed"
    """An anatomy scan has failed."""

    ANATOMY_UPDATED = "context:anatomy_updated"
    """The anatomy store has been updated (new symbols, modified files)."""

    # BugLog
    BUG_LOGGED = "context:bug_logged"
    """A new bug has been recorded."""

    BUG_DUPLICATED = "context:bug_duplicated"
    """A bug was identified as a duplicate of an existing one."""

    BUG_STATUS_CHANGED = "context:bug_status_changed"
    """A bug's status has been updated (resolved, ignored, etc.)."""

    # Token
    TOKEN_LEDGER_UPDATED = "context:token_ledger_updated"
    """Token usage has been recorded."""

    TOKEN_BUDGET_WARNING = "context:token_budget_warning"
    """Token usage is approaching the budget limit (e.g., >80%)."""

    TOKEN_BUDGET_EXCEEDED = "context:token_budget_exceeded"
    """Token budget has been exceeded."""

    TOKEN_WASTE_DETECTED = "context:token_waste_detected"
    """A wasteful token usage pattern has been detected."""

    # Cerebrum
    MEMORY_STORED = "context:memory_stored"
    """A new memory has been stored in the cerebrum."""

    MEMORY_RECALLED = "context:memory_recalled"
    """A memory has been accessed (recalled)."""

    MEMORY_FORGOTTEN = "context:memory_forgotten"
    """A memory has been removed."""

    MEMORY_TTL_EXPIRED = "context:memory_ttl_expired"
    """One or more memories have expired due to TTL."""

    # File watching
    FILE_WATCH_STARTED = "context:file_watch_started"
    """File watching has been started for a project."""

    FILE_WATCH_STOPPED = "context:file_watch_stopped"
    """File watching has been stopped."""

    FILE_CHANGED = "context:file_changed"
    """A watched file has been modified (created, updated, deleted)."""

    # Context generation
    CONTEXT_GENERATED = "context:context_generated"
    """A context string has been generated for a session."""

    # Desktop (future)
    DESKTOP_NODE_REGISTERED = "desktop:node_registered"
    """A desktop agent node has registered."""

    DESKTOP_NODE_DISCONNECTED = "desktop:node_disconnected"
    """A desktop agent node has disconnected."""

    DESKTOP_ACTION_COMPLETED = "desktop:action_completed"
    """A desktop automation action has completed."""

    DESKTOP_ACTION_FAILED = "desktop:action_failed"
    """A desktop automation action has failed."""


# Event payload schemas (documentation only — these are dicts at runtime)

SKPL_EVENT_PAYLOADS = {
    SKPLContextEventName.ANATOMY_SCAN_PROGRESS: {
        "description": "Progress update during anatomy scan",
        "fields": {
            "files_scanned": "int — Number of files processed",
            "total_files": "int — Total files to scan",
            "symbols_extracted": "int — Symbols extracted so far",
            "current_file": "str — Currently processing file",
            "progress_pct": "float — Progress percentage (0-100)",
        },
    },
    SKPLContextEventName.ANATOMY_SCAN_COMPLETED: {
        "description": "Anatomy scan completed successfully",
        "fields": {
            "files_scanned": "int — Total files scanned",
            "symbols_extracted": "int — Total symbols extracted",
            "duration_seconds": "float — Scan duration",
            "languages": "list[str] — Languages found",
            "errors": "list[str] — Any non-fatal errors",
        },
    },
    SKPLContextEventName.TOKEN_BUDGET_WARNING: {
        "description": "Token usage approaching budget limit",
        "fields": {
            "budget": "int — Token budget",
            "used": "int — Tokens used",
            "remaining": "int — Tokens remaining",
            "usage_pct": "float — Usage percentage",
        },
    },
    SKPLContextEventName.TOKEN_WASTE_DETECTED: {
        "description": "Wasteful token usage pattern detected",
        "fields": {
            "pattern_type": "str — Type of waste pattern",
            "severity": "str — Severity: low, medium, high",
            "tokens_wasted": "int — Estimated tokens wasted",
            "description": "str — Human-readable description",
        },
    },
}