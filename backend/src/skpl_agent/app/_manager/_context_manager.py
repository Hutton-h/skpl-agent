"""
Context Manager — Application-wide context lifecycle management.

Manages session context instances, coordinates lifecycle hooks,
and provides a unified interface for the API layer to interact
with the context management system.

This is the bridge between the HTTP API layer and the context
subsystem. It handles:
- Creating and caching session contexts
- Coordinating anatomy scans
- Aggregating context summaries
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from skpl_agent.context.anatomy_scanner import AnatomyScanner, ScanMode, ScanOptions, ScanResult
from skpl_agent.context.anatomy_store import AnatomyStore, AnatomyStoreMode, AnatomyStoreProtocol
from skpl_agent.context.buglog import BugLog, BugRecord
from skpl_agent.context.cerebrum import Cerebrum, Memory
from skpl_agent.context.session_context import SessionContextConfig, SessionContextManager
from skpl_agent.context.token_ledger import TokenLedgerSummary

logger = logging.getLogger(__name__)


class ContextManager:
    """Application-wide context manager.

    Usage:
        mgr = ContextManager()
        ctx = await mgr.get_session_context(session_id="sess-123")
        result = await mgr.scan_project("/path/to/project")
    """

    def __init__(
        self,
        default_config: SessionContextConfig | None = None,
        max_cached_sessions: int = 100,
    ):
        self.default_config = default_config or SessionContextConfig()
        self.max_cached_sessions = max_cached_sessions
        self._sessions: dict[str, SessionContextManager] = {}
        self._scan_tasks: dict[str, asyncio.Task] = {}

    # -- Session Management --

    async def get_session_context(
        self,
        session_id: str,
        agent_id: str | None = None,
        config: SessionContextConfig | None = None,
    ) -> SessionContextManager:
        """Get or create a session context."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        ctx = SessionContextManager(
            session_id=session_id,
            agent_id=agent_id,
            config=config or self.default_config,
        )
        await ctx.initialize()

        # Cache the session
        if len(self._sessions) >= self.max_cached_sessions:
            # Evict oldest
            oldest = next(iter(self._sessions))
            await self._sessions[oldest].shutdown()
            del self._sessions[oldest]

        self._sessions[session_id] = ctx
        return ctx

    async def close_session(self, session_id: str) -> None:
        """Close and remove a session context."""
        ctx = self._sessions.pop(session_id, None)
        if ctx:
            ctx.shutdown()
            logger.info("Session %s closed", session_id)

    async def close_all(self) -> None:
        """Close all sessions."""
        for session_id, ctx in list(self._sessions.items()):
            ctx.shutdown()
        self._sessions.clear()
        logger.info("All sessions closed")

    # -- Anatomy Scanning --

    async def scan_project(
        self,
        root_path: str | Path,
        session_id: str | None = None,
        mode: ScanMode = ScanMode.FULL,
        changed_files: list[str] | None = None,
        on_progress: callable | None = None,
    ) -> ScanResult:
        """Scan a project for symbols."""
        options = ScanOptions(
            mode=mode,
            root_path=Path(root_path),
            changed_files=changed_files or [],
            on_progress=on_progress,
        )
        scanner = AnatomyScanner(options)
        try:
            result = await scanner.scan()
            return result
        finally:
            scanner.close()

    async def scan_project_async(
        self,
        root_path: str | Path,
        session_id: str | None = None,
    ) -> str:
        """Start an async scan and return a task ID for polling."""
        task_id = f"scan_{session_id or 'anon'}_{asyncio.get_running_loop().time()}"

        async def _run_scan():
            return await self.scan_project(root_path, session_id)

        self._scan_tasks[task_id] = asyncio.create_task(_run_scan())
        return task_id

    def get_scan_status(self, task_id: str) -> dict | None:
        """Get the status of an async scan task."""
        task = self._scan_tasks.get(task_id)
        if task is None:
            return None

        if task.done():
            if task.exception():
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(task.exception()),
                }
            result = task.result()
            return {
                "task_id": task_id,
                "status": "completed",
                "result": {
                    "files_scanned": result.total_files_scanned,
                    "symbols_extracted": result.total_symbols_extracted,
                    "duration_seconds": result.duration_seconds,
                    "languages": result.languages_found,
                },
            }
        return {
            "task_id": task_id,
            "status": "running",
        }

    # -- Context Generation --

    def generate_context(
        self,
        session_id: str,
        include_anatomy: bool = True,
        include_bugs: bool = True,
        include_memory: bool = True,
    ) -> str:
        """Generate context string for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return ""
        return ctx.generate_context(
            include_anatomy=include_anatomy,
            include_bugs=include_bugs,
            include_memory=include_memory,
        )

    # -- Bug Management --

    def log_bug(
        self,
        session_id: str,
        error_type: str,
        error_message: str,
        error_traceback: str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> BugRecord | None:
        """Log a bug for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return None
        return ctx.log_bug(
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
            file_path=file_path,
            line_number=line_number,
        )

    def get_recent_bugs(self, session_id: str, limit: int = 10) -> list[BugRecord]:
        """Get recent bugs for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return []
        return ctx.get_recent_bugs(limit)

    # -- Memory Management --

    def remember(
        self,
        session_id: str,
        key: str,
        value: str,
        category: str = "general",
        confidence: float = 1.0,
    ) -> Memory | None:
        """Store a memory for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return None
        return ctx.remember(key, value, category, confidence)

    def recall(self, session_id: str, key: str) -> Memory | None:
        """Retrieve a memory for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return None
        return ctx.recall(key)

    # -- Summary --

    def get_summary(self, session_id: str) -> dict | None:
        """Get comprehensive session summary."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return None
        return ctx.get_summary()

    def get_token_summary(self, session_id: str) -> TokenLedgerSummary | None:
        """Get token usage summary for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return None
        return ctx.get_token_summary()

    # -- Store Access --

    def get_store(self, session_id: str) -> AnatomyStoreProtocol | None:
        """Get the anatomy store for a session."""
        ctx = self._sessions.get(session_id)
        if ctx is None:
            return None
        return ctx.scanner.store

    def search_symbols(
        self,
        session_id: str,
        query: str,
        language: str | None = None,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search anatomy symbols."""
        store = self.get_store(session_id)
        if store is None:
            return []
        return store.search_symbols(query, language, kind, limit)