"""
Session Context Manager — Orchestrates context management per session.

Provides a unified interface for session-based context management:
- Anatomy scanning (project symbol extraction)
- Bug logging and deduplication
- Token tracking and waste detection
- Cerebrum memory persistence
- Context injection (generating prompts for agents)

This is the central coordinator that wires together all context
subsystems for a single agent session.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from skpl_agent.context.anatomy_scanner import AnatomyScanner, ScanMode, ScanOptions, ScanResult
from skpl_agent.context.anatomy_store import AnatomyStore, AnatomyStoreMode
from skpl_agent.context.buglog import BugLog, BugRecord, BugStatus
from skpl_agent.context.cerebrum import Cerebrum, Memory
from skpl_agent.context.token_estimator import TokenEstimator
from skpl_agent.context.token_ledger import BudgetExceededError, TokenLedger, TokenLedgerSummary
from skpl_agent.context.waste_detector import WasteDetector, WastePattern


# ---------------------------------------------------------------------------
# Session Context
# ---------------------------------------------------------------------------


@dataclass
class SessionContextConfig:
    """Configuration for a session context."""

    project_root: str | Path = "."
    anatomy_enabled: bool = True
    buglog_enabled: bool = True
    cerebrum_enabled: bool = True
    token_tracking_enabled: bool = True
    waste_detection_enabled: bool = True
    auto_scan_on_start: bool = False
    scan_mode: ScanMode = ScanMode.FULL
    store_mode: AnatomyStoreMode = AnatomyStoreMode.SQLITE
    store_path: str = ".skpl/anatomy.db"
    token_budget: int | None = None
    max_context_tokens: int = 8000
    max_workers: int = 4
    filter_sensitive: bool = True


class SessionContextManager:
    """Manages all context subsystems for a single agent session.

    Usage:
        ctx = SessionContextManager(
            session_id="sess-123",
            agent_id="agent-456",
            config=SessionContextConfig(project_root="/path/to/project"),
        )
        await ctx.initialize()
        # ... agent runs ...
        ctx.record_token_usage(input_tokens=500, output_tokens=200)
        ctx.log_bug(error_type="ValueError", error_message="...")
        ctx.remember("user_prefers_python", "yes")
        summary = ctx.get_summary()
    """

    def __init__(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        config: SessionContextConfig | None = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_id = agent_id
        self.config = config or SessionContextConfig()
        self.created_at = datetime.now(timezone.utc)

        # Subsystems (lazy-initialized)
        self._scanner: AnatomyScanner | None = None
        self._buglog: BugLog | None = None
        self._cerebrum: Cerebrum | None = None
        self._token_ledger: TokenLedger | None = None
        self._waste_detector: WasteDetector | None = None
        self._estimator: TokenEstimator | None = None

        # State
        self._initialized: bool = False
        self._last_scan: ScanResult | None = None

    # -- Properties --

    @property
    def scanner(self) -> AnatomyScanner:
        if self._scanner is None:
            options = ScanOptions(
                mode=self.config.scan_mode,
                root_path=Path(self.config.project_root),
                max_workers=self.config.max_workers,
                store_mode=self.config.store_mode,
                store_path=self.config.store_path,
                filter_sensitive=self.config.filter_sensitive,
            )
            self._scanner = AnatomyScanner(options)
        return self._scanner

    @property
    def buglog(self) -> BugLog:
        if self._buglog is None:
            self._buglog = BugLog(session_id=self.session_id)
        return self._buglog

    @property
    def cerebrum(self) -> Cerebrum:
        if self._cerebrum is None:
            self._cerebrum = Cerebrum(agent_id=self.agent_id or "")
        return self._cerebrum

    @property
    def token_ledger(self) -> TokenLedger:
        if self._token_ledger is None:
            self._token_ledger = TokenLedger(
                session_id=self.session_id,
                agent_id=self.agent_id,
                token_budget=self.config.token_budget,
            )
        return self._token_ledger

    @property
    def waste_detector(self) -> WasteDetector:
        if self._waste_detector is None:
            self._waste_detector = WasteDetector()
        return self._waste_detector

    @property
    def estimator(self) -> TokenEstimator:
        if self._estimator is None:
            self._estimator = TokenEstimator()
        return self._estimator

    # -- Lifecycle --

    async def initialize(self) -> None:
        """Initialize all context subsystems.

        If auto_scan_on_start is True, performs an initial anatomy scan.
        """
        if self._initialized:
            return

        if self.config.anatomy_enabled and self.config.auto_scan_on_start:
            self._last_scan = await self.scanner.scan()

        self._initialized = True

    def shutdown(self) -> None:
        """Clean up all subsystems."""
        if self._scanner:
            self._scanner.close()
        self._initialized = False

    # -- Anatomy Scanning --

    async def scan_project(
        self,
        mode: ScanMode | None = None,
        changed_files: list[str] | None = None,
    ) -> ScanResult:
        """Scan the project for symbols."""
        if mode:
            self.scanner.options.mode = mode
        if changed_files:
            self.scanner.options.changed_files = changed_files
            self.scanner.options.mode = ScanMode.INCREMENTAL

        self._last_scan = await self.scanner.scan()
        return self._last_scan

    def get_last_scan(self) -> ScanResult | None:
        return self._last_scan

    def search_symbols(
        self, query: str, language: str | None = None, kind: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Search for symbols in the anatomy store."""
        return self.scanner.store.search_symbols(query, language, kind, limit)

    def get_file_symbols(self, file_path: str) -> list[dict]:
        """Get symbols for a specific file."""
        return self.scanner.store.get_file_symbols(file_path)

    # -- Bug Logging --

    def log_bug(
        self,
        error_type: str,
        error_message: str,
        error_traceback: str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
        metadata: dict | None = None,
    ) -> BugRecord:
        """Log a bug encountered during agent execution."""
        if not self.config.buglog_enabled:
            return BugRecord()

        return self.buglog.log(
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
            file_path=file_path,
            line_number=line_number,
            agent_id=self.agent_id,
            metadata=metadata,
        )

    def get_recent_bugs(self, limit: int = 10) -> list[BugRecord]:
        return self.buglog.get_recent(limit)

    def get_open_bugs(self) -> list[BugRecord]:
        return self.buglog.get_open()

    # -- Memory --

    def remember(
        self,
        key: str,
        value: str,
        category: str = "general",
        confidence: float = 1.0,
        ttl_seconds: int | None = None,
    ) -> Memory:
        """Store a memory."""
        if not self.config.cerebrum_enabled:
            return Memory()

        return self.cerebrum.remember(
            key=key,
            value=value,
            category=category,
            confidence=confidence,
            ttl_seconds=ttl_seconds,
        )

    def recall(self, key: str) -> Memory | None:
        """Retrieve a memory."""
        if not self.config.cerebrum_enabled:
            return None
        return self.cerebrum.recall(key)

    def forget(self, key: str) -> bool:
        """Remove a memory."""
        if not self.config.cerebrum_enabled:
            return False
        return self.cerebrum.forget(key)

    # -- Token Tracking --

    def record_token_usage(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model_name: str | None = None,
        is_waste: bool = False,
        waste_reason: str | None = None,
    ) -> None:
        """Record token usage."""
        if not self.config.token_tracking_enabled:
            return

        self.token_ledger.record(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
            is_waste=is_waste,
            waste_reason=waste_reason,
        )

    def check_budget(self) -> None:
        """Check if token budget is exceeded. Raises BudgetExceededError."""
        if self.token_ledger.is_over_budget():
            raise BudgetExceededError(
                self.config.token_budget or 0,
                self.token_ledger.total_tokens,
            )

    def get_token_summary(self) -> TokenLedgerSummary:
        return self.token_ledger.get_summary()

    # -- Waste Detection --

    def record_file_read(self, file_path: str, token_count: int = 0) -> None:
        """Record a file read for waste detection."""
        if self.config.waste_detection_enabled:
            self.waste_detector.record_file_read(file_path, token_count)

    def is_wasteful_read(self, file_path: str) -> bool:
        if not self.config.waste_detection_enabled:
            return False
        return self.waste_detector.is_wasteful_read(file_path)

    def get_waste_patterns(self) -> list[WastePattern]:
        return self.waste_detector.get_patterns()

    # -- Context Injection --

    def generate_context(
        self,
        include_anatomy: bool = True,
        include_bugs: bool = True,
        include_memory: bool = True,
        max_anatomy_entries: int = 50,
        max_bug_entries: int = 10,
        max_memory_entries: int = 50,
    ) -> str:
        """Generate a context string for injection into agent prompts.

        This is the main output of the context management system:
        a formatted string containing relevant project anatomy, recent
        bugs, and learned memories that the agent can use to make
        better decisions.
        """
        parts: list[str] = []

        if include_anatomy and self.config.anatomy_enabled:
            anatomy_str = self._generate_anatomy_context(max_anatomy_entries)
            if anatomy_str:
                parts.append(anatomy_str)

        if include_bugs and self.config.buglog_enabled:
            bugs_str = self._generate_bug_context(max_bug_entries)
            if bugs_str:
                parts.append(bugs_str)

        if include_memory and self.config.cerebrum_enabled:
            memory_str = self.cerebrum.export_context(max_memory_entries)
            if memory_str:
                parts.append(memory_str)

        return "\n\n".join(parts)

    def _generate_anatomy_context(self, max_entries: int = 50) -> str:
        """Generate project anatomy context string."""
        store = self.scanner.store
        stats = store.get_stats()

        if stats["total_symbols"] == 0:
            return ""

        lines = [
            "## Project Anatomy",
            f"Total symbols: {stats['total_symbols']} | Files: {stats['total_files']}",
            f"Languages: {', '.join(f'{lang}({count})' for lang, count in list(stats.get('languages', {}).items())[:10])}",
            "",
            "### Key Symbols",
        ]

        # Get top symbols (most exported, most referenced)
        # For now, just get all symbols and limit
        results = store.search_symbols("", limit=max_entries)
        for sym in results:
            export_marker = " (exported)" if sym.get("is_exported") else ""
            sig = sym.get("signature", "")
            line = f"- [{sym.get('language', '')}] {sym.get('kind', '')}: {sym.get('name', '')}"
            if sig:
                line += f" `{sig}`"
            line += export_marker
            if sym.get("description"):
                line += f" — {sym.get('description')[:100]}"
            lines.append(line)

        return "\n".join(lines)

    def _generate_bug_context(self, max_entries: int = 10) -> str:
        """Generate bug context string."""
        bugs = self.buglog.get_recent(max_entries)
        if not bugs:
            return ""

        lines = [
            "## Recent Bugs",
            f"Showing {len(bugs)} most recent bugs",
            "",
        ]

        for bug in bugs:
            lines.append(f"- [{bug.error_type}] {bug.error_message[:200]}")
            if bug.resolution:
                lines.append(f"  Resolution: {bug.resolution[:200]}")

        return "\n".join(lines)

    # -- Summary --

    def get_summary(self) -> dict:
        """Get a comprehensive summary of all context subsystems."""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "anatomy": self.scanner.store.get_stats() if self.config.anatomy_enabled else None,
            "bugs": self.buglog.get_stats() if self.config.buglog_enabled else None,
            "memory": self.cerebrum.get_stats() if self.config.cerebrum_enabled else None,
            "tokens": (
                self.token_ledger.get_summary().__dict__
                if self.config.token_tracking_enabled
                else None
            ),
            "waste": self.waste_detector.get_waste_summary() if self.config.waste_detection_enabled else None,
            "last_scan": (
                {
                    "mode": self._last_scan.mode.value,
                    "files_scanned": self._last_scan.total_files_scanned,
                    "symbols_extracted": self._last_scan.total_symbols_extracted,
                    "duration_seconds": self._last_scan.duration_seconds,
                }
                if self._last_scan
                else None
            ),
        }