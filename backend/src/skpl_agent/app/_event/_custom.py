"""SKPL Agent custom event definitions.

Events bridge the context subsystem with AgentScope's event bus, enabling
real-time notifications for anatomy scanning, context updates, bug tracking,
and desktop agent operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


# ── Context Events ───────────────────────────────────────────────────────────


@dataclass
class ContextSessionCreated:
    """Emitted when a new context session is created."""

    session_id: str
    agent_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ContextSessionClosed:
    """Emitted when a context session is closed."""

    session_id: str
    reason: str = "explicit"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Anatomy Events ───────────────────────────────────────────────────────────


@dataclass
class AnatomyScanStarted:
    """Emitted when an anatomy scan begins."""

    session_id: str
    task_id: str
    root_path: str
    mode: str  # full | incremental
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AnatomyScanProgress:
    """Emitted periodically during an anatomy scan."""

    session_id: str
    task_id: str
    files_scanned: int
    symbols_extracted: int
    current_file: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AnatomyScanCompleted:
    """Emitted when an anatomy scan finishes successfully."""

    session_id: str
    task_id: str
    total_files: int
    total_symbols: int
    duration_seconds: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AnatomyScanFailed:
    """Emitted when an anatomy scan fails."""

    session_id: str
    task_id: str
    error: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Bug Events ───────────────────────────────────────────────────────────────


@dataclass
class BugLogged:
    """Emitted when a new bug is logged."""

    session_id: str
    bug_id: str
    error_type: str
    error_message: str
    file_path: str | None = None
    line_number: int | None = None
    is_duplicate: bool = False
    duplicate_of: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BugStatusUpdated:
    """Emitted when a bug's status changes."""

    session_id: str
    bug_id: str
    old_status: str
    new_status: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Token Events ─────────────────────────────────────────────────────────────


@dataclass
class TokenUsageRecorded:
    """Emitted when token usage is recorded."""

    session_id: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WasteDetected:
    """Emitted when token waste is detected."""

    session_id: str
    wasted_tokens: int
    waste_rate: float
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Desktop Events ───────────────────────────────────────────────────────────


@dataclass
class DesktopNodeConnected:
    """Emitted when a desktop agent node connects."""

    node_id: str
    name: str
    hostname: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DesktopNodeDisconnected:
    """Emitted when a desktop agent node disconnects."""

    node_id: str
    name: str
    reason: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DesktopActionStarted:
    """Emitted when a desktop action begins execution."""

    node_id: str
    action_id: str
    action_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DesktopActionCompleted:
    """Emitted when a desktop action completes."""

    node_id: str
    action_id: str
    action_type: str
    success: bool
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Firecrawl Events ─────────────────────────────────────────────────────────


@dataclass
class CrawlStarted:
    """Emitted when a Firecrawl crawl begins."""

    crawl_id: str
    url: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CrawlCompleted:
    """Emitted when a Firecrawl crawl completes."""

    crawl_id: str
    url: str
    pages_crawled: int
    pages_failed: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Event Registry ───────────────────────────────────────────────────────────

# All custom event types, keyed by event name for dispatch
CUSTOM_EVENT_TYPES: dict[str, type] = {
    "context.session.created": ContextSessionCreated,
    "context.session.closed": ContextSessionClosed,
    "anatomy.scan.started": AnatomyScanStarted,
    "anatomy.scan.progress": AnatomyScanProgress,
    "anatomy.scan.completed": AnatomyScanCompleted,
    "anatomy.scan.failed": AnatomyScanFailed,
    "bug.logged": BugLogged,
    "bug.status.updated": BugStatusUpdated,
    "token.usage.recorded": TokenUsageRecorded,
    "token.waste.detected": WasteDetected,
    "desktop.node.connected": DesktopNodeConnected,
    "desktop.node.disconnected": DesktopNodeDisconnected,
    "desktop.action.started": DesktopActionStarted,
    "desktop.action.completed": DesktopActionCompleted,
    "firecrawl.crawl.started": CrawlStarted,
    "firecrawl.crawl.completed": CrawlCompleted,
}