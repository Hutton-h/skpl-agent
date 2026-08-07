"""SKPL Context Event Emitter — Bridges context lifecycle to AgentScope event bus.

Dispatches CustomEvent instances through the agent's event bus whenever
context operations occur (scan, bug, memory, token, file watch). This
enables the frontend to receive real-time updates on context activity.

Usage:
    emitter = ContextEventEmitter(agent)
    await emitter.emit_scan_started(session_id, root_path, mode)
    await emitter.emit_scan_progress(session_id, files_scanned, total_files)
    await emitter.emit_scan_completed(session_id, result)
    await emitter.emit_bug_logged(session_id, bug_record)
    await emitter.emit_token_budget_warning(session_id, budget, used)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from skpl_agent.event._custom import SKPLContextEventName, SKPL_EVENT_PAYLOADS

if TYPE_CHECKING:
    from skpl_agent.agent import Agent

logger = logging.getLogger(__name__)


class ContextEventEmitter:
    """Emits SKPL context events through AgentScope's event bus.

    All emit methods are non-blocking — failures are logged and swallowed
    to ensure context operations are not blocked by event delivery issues.
    """

    def __init__(self, agent: "Agent | None" = None):
        self._agent = agent

    def bind(self, agent: "Agent") -> None:
        """Bind to an agent instance for event emission."""
        self._agent = agent

    # ── Session Lifecycle ──────────────────────────────────────────────────

    async def emit_session_started(
        self,
        session_id: str,
        agent_id: str | None = None,
        project_root: str = ".",
    ) -> None:
        """Emit context:session_started event."""
        await self._emit(
            SKPLContextEventName.CONTEXT_SESSION_STARTED,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "project_root": project_root,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def emit_session_ended(
        self,
        session_id: str,
        agent_id: str | None = None,
        stats: dict | None = None,
    ) -> None:
        """Emit context:session_ended event."""
        await self._emit(
            SKPLContextEventName.CONTEXT_SESSION_ENDED,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "stats": stats or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # ── Anatomy Scan ───────────────────────────────────────────────────────

    async def emit_scan_started(
        self,
        session_id: str,
        root_path: str,
        mode: str = "full",
    ) -> None:
        """Emit context:anatomy_scan_started event."""
        await self._emit(
            SKPLContextEventName.ANATOMY_SCAN_STARTED,
            {
                "session_id": session_id,
                "root_path": root_path,
                "mode": mode,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def emit_scan_progress(
        self,
        session_id: str,
        files_scanned: int,
        total_files: int,
        symbols_extracted: int = 0,
        current_file: str = "",
    ) -> None:
        """Emit context:anatomy_scan_progress event."""
        progress_pct = (
            (files_scanned / total_files * 100) if total_files > 0 else 0.0
        )
        await self._emit(
            SKPLContextEventName.ANATOMY_SCAN_PROGRESS,
            {
                "session_id": session_id,
                "files_scanned": files_scanned,
                "total_files": total_files,
                "symbols_extracted": symbols_extracted,
                "current_file": current_file,
                "progress_pct": round(progress_pct, 1),
            },
        )

    async def emit_scan_completed(
        self,
        session_id: str,
        files_scanned: int,
        symbols_extracted: int,
        duration_seconds: float,
        languages: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        """Emit context:anatomy_scan_completed event."""
        await self._emit(
            SKPLContextEventName.ANATOMY_SCAN_COMPLETED,
            {
                "session_id": session_id,
                "files_scanned": files_scanned,
                "symbols_extracted": symbols_extracted,
                "duration_seconds": round(duration_seconds, 2),
                "languages": languages or [],
                "errors": errors or [],
            },
        )

    async def emit_scan_failed(
        self,
        session_id: str,
        error: str,
        root_path: str = "",
    ) -> None:
        """Emit context:anatomy_scan_failed event."""
        await self._emit(
            SKPLContextEventName.ANATOMY_SCAN_FAILED,
            {
                "session_id": session_id,
                "error": error,
                "root_path": root_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def emit_anatomy_updated(
        self,
        session_id: str,
        changed_files: list[str],
        symbols_added: int = 0,
        symbols_removed: int = 0,
    ) -> None:
        """Emit context:anatomy_updated event."""
        await self._emit(
            SKPLContextEventName.ANATOMY_UPDATED,
            {
                "session_id": session_id,
                "changed_files": changed_files,
                "symbols_added": symbols_added,
                "symbols_removed": symbols_removed,
            },
        )

    # ── BugLog ─────────────────────────────────────────────────────────────

    async def emit_bug_logged(
        self,
        session_id: str,
        bug_id: str,
        error_type: str,
        error_message: str,
        file_path: str | None = None,
        line_number: int | None = None,
        is_duplicate: bool = False,
    ) -> None:
        """Emit context:bug_logged or context:bug_duplicated event."""
        name = (
            SKPLContextEventName.BUG_DUPLICATED
            if is_duplicate
            else SKPLContextEventName.BUG_LOGGED
        )
        await self._emit(
            name,
            {
                "session_id": session_id,
                "bug_id": bug_id,
                "error_type": error_type,
                "error_message": error_message[:200],
                "file_path": file_path,
                "line_number": line_number,
            },
        )

    async def emit_bug_status_changed(
        self,
        session_id: str,
        bug_id: str,
        old_status: str,
        new_status: str,
        resolution: str | None = None,
    ) -> None:
        """Emit context:bug_status_changed event."""
        await self._emit(
            SKPLContextEventName.BUG_STATUS_CHANGED,
            {
                "session_id": session_id,
                "bug_id": bug_id,
                "old_status": old_status,
                "new_status": new_status,
                "resolution": resolution,
            },
        )

    # ── Token ──────────────────────────────────────────────────────────────

    async def emit_token_ledger_updated(
        self,
        session_id: str,
        total_tokens: int,
        input_tokens: int,
        output_tokens: int,
        model_name: str | None = None,
    ) -> None:
        """Emit context:token_ledger_updated event."""
        await self._emit(
            SKPLContextEventName.TOKEN_LEDGER_UPDATED,
            {
                "session_id": session_id,
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model_name": model_name,
            },
        )

    async def emit_token_budget_warning(
        self,
        session_id: str,
        budget: int,
        used: int,
        remaining: int,
        usage_pct: float,
    ) -> None:
        """Emit context:token_budget_warning event."""
        await self._emit(
            SKPLContextEventName.TOKEN_BUDGET_WARNING,
            {
                "session_id": session_id,
                "budget": budget,
                "used": used,
                "remaining": remaining,
                "usage_pct": round(usage_pct, 1),
            },
        )

    async def emit_token_budget_exceeded(
        self,
        session_id: str,
        budget: int,
        used: int,
    ) -> None:
        """Emit context:token_budget_exceeded event."""
        await self._emit(
            SKPLContextEventName.TOKEN_BUDGET_EXCEEDED,
            {
                "session_id": session_id,
                "budget": budget,
                "used": used,
                "exceeded_by": used - budget,
            },
        )

    async def emit_token_waste_detected(
        self,
        session_id: str,
        pattern_type: str,
        severity: str,
        tokens_wasted: int,
        description: str,
    ) -> None:
        """Emit context:token_waste_detected event."""
        await self._emit(
            SKPLContextEventName.TOKEN_WASTE_DETECTED,
            {
                "session_id": session_id,
                "pattern_type": pattern_type,
                "severity": severity,
                "tokens_wasted": tokens_wasted,
                "description": description,
            },
        )

    # ── Cerebrum ───────────────────────────────────────────────────────────

    async def emit_memory_stored(
        self,
        session_id: str,
        agent_id: str | None,
        key: str,
        category: str,
        confidence: float,
    ) -> None:
        """Emit context:memory_stored event."""
        await self._emit(
            SKPLContextEventName.MEMORY_STORED,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "key": key,
                "category": category,
                "confidence": confidence,
            },
        )

    async def emit_memory_recalled(
        self,
        session_id: str,
        agent_id: str | None,
        key: str,
        access_count: int,
    ) -> None:
        """Emit context:memory_recalled event."""
        await self._emit(
            SKPLContextEventName.MEMORY_RECALLED,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "key": key,
                "access_count": access_count,
            },
        )

    async def emit_memory_forgotten(
        self,
        session_id: str,
        agent_id: str | None,
        key: str,
    ) -> None:
        """Emit context:memory_forgotten event."""
        await self._emit(
            SKPLContextEventName.MEMORY_FORGOTTEN,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "key": key,
            },
        )

    async def emit_memory_ttl_expired(
        self,
        session_id: str,
        agent_id: str | None,
        expired_keys: list[str],
    ) -> None:
        """Emit context:memory_ttl_expired event."""
        await self._emit(
            SKPLContextEventName.MEMORY_TTL_EXPIRED,
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "expired_keys": expired_keys,
                "count": len(expired_keys),
            },
        )

    # ── File Watching ──────────────────────────────────────────────────────

    async def emit_file_watch_started(
        self,
        session_id: str,
        root_path: str,
        pattern_count: int = 0,
    ) -> None:
        """Emit context:file_watch_started event."""
        await self._emit(
            SKPLContextEventName.FILE_WATCH_STARTED,
            {
                "session_id": session_id,
                "root_path": root_path,
                "pattern_count": pattern_count,
            },
        )

    async def emit_file_watch_stopped(
        self,
        session_id: str,
        root_path: str = "",
    ) -> None:
        """Emit context:file_watch_stopped event."""
        await self._emit(
            SKPLContextEventName.FILE_WATCH_STOPPED,
            {
                "session_id": session_id,
                "root_path": root_path,
            },
        )

    async def emit_file_changed(
        self,
        session_id: str,
        file_path: str,
        change_type: str,  # created, modified, deleted
    ) -> None:
        """Emit context:file_changed event."""
        await self._emit(
            SKPLContextEventName.FILE_CHANGED,
            {
                "session_id": session_id,
                "file_path": file_path,
                "change_type": change_type,
            },
        )

    # ── Context Generation ─────────────────────────────────────────────────

    async def emit_context_generated(
        self,
        session_id: str,
        estimated_tokens: int,
        sections: list[str] | None = None,
    ) -> None:
        """Emit context:context_generated event."""
        await self._emit(
            SKPLContextEventName.CONTEXT_GENERATED,
            {
                "session_id": session_id,
                "estimated_tokens": estimated_tokens,
                "sections": sections or [],
            },
        )

    # ── Desktop (future) ───────────────────────────────────────────────────

    async def emit_desktop_node_registered(
        self,
        node_id: str,
        hostname: str,
        capabilities: list[str] | None = None,
    ) -> None:
        """Emit desktop:node_registered event."""
        await self._emit(
            SKPLContextEventName.DESKTOP_NODE_REGISTERED,
            {
                "node_id": node_id,
                "hostname": hostname,
                "capabilities": capabilities or [],
            },
        )

    async def emit_desktop_node_disconnected(
        self,
        node_id: str,
        reason: str = "",
    ) -> None:
        """Emit desktop:node_disconnected event."""
        await self._emit(
            SKPLContextEventName.DESKTOP_NODE_DISCONNECTED,
            {
                "node_id": node_id,
                "reason": reason,
            },
        )

    async def emit_desktop_action_completed(
        self,
        node_id: str,
        action_type: str,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """Emit desktop:action_completed event."""
        await self._emit(
            SKPLContextEventName.DESKTOP_ACTION_COMPLETED,
            {
                "node_id": node_id,
                "action_type": action_type,
                "duration_ms": duration_ms,
                "success": success,
            },
        )

    async def emit_desktop_action_failed(
        self,
        node_id: str,
        action_type: str,
        error: str,
    ) -> None:
        """Emit desktop:action_failed event."""
        await self._emit(
            SKPLContextEventName.DESKTOP_ACTION_FAILED,
            {
                "node_id": node_id,
                "action_type": action_type,
                "error": error,
            },
        )

    # ── Internal ───────────────────────────────────────────────────────────

    async def _emit(self, name: str, value: dict) -> None:
        """Emit a CustomEvent through the agent's event bus if available.

        This is non-blocking — if the agent is not available or the
        event bus rejects the event, we log and continue.
        """
        if self._agent is None:
            logger.debug("No agent bound, skipping event: %s", name)
            return

        try:
            from skpl_agent.event._event import CustomEvent

            event = CustomEvent(name=name, value=value)
            await self._agent.emit_event(event)
        except Exception as e:
            logger.debug("Failed to emit event %s: %s", name, e)