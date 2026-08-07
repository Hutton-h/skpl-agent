"""Request/response schemas for the context router.

Covers all context-related endpoints:
- Anatomy scanning
- Bug logging
- Memory (cerebrum)
- Token tracking
- Context generation
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Anatomy Scanning
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    """Request to start an anatomy scan."""
    root_path: str = Field(
        default=".",
        description="Root directory to scan. Defaults to current directory.",
    )
    mode: str = Field(
        default="full",
        pattern="^(full|incremental)$",
        description="Scan mode: 'full' or 'incremental'.",
    )
    changed_files: list[str] = Field(
        default_factory=list,
        description="List of changed files for incremental scans.",
    )


class ScanStatusResponse(BaseModel):
    """Status of a scan task."""
    task_id: str = Field(description="Unique scan task identifier.")
    status: str = Field(description="Task status: queued, running, completed, failed, cancelled.")
    progress: int = Field(default=0, description="Number of files processed.")
    progress_total: int = Field(default=0, description="Total number of files to scan.")
    current_file: str = Field(default="", description="Currently processing file.")
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    result: dict | None = Field(default=None, description="Scan result (only when completed).")
    error: str | None = Field(default=None, description="Error message (only when failed).")


class SymbolSearchRequest(BaseModel):
    """Request to search anatomy symbols."""
    query: str = Field(description="Search query for symbol names, signatures, or descriptions.")
    language: str | None = Field(default=None, description="Filter by programming language.")
    kind: str | None = Field(
        default=None,
        description="Filter by symbol kind: function, class, method, variable, interface, etc.",
    )
    limit: int = Field(default=50, ge=1, le=200, description="Max results to return.")


class SymbolResponse(BaseModel):
    """A single symbol from the anatomy store."""
    id: str
    name: str
    kind: str
    language: str
    line_start: int
    line_end: int
    signature: str | None = None
    description: str | None = None
    parent: str | None = None
    is_exported: bool = False
    file_path: str = ""


class AnatomyStatsResponse(BaseModel):
    """Anatomy store statistics."""
    total_symbols: int = 0
    total_files: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    backend: str = ""


# ---------------------------------------------------------------------------
# Bug Log
# ---------------------------------------------------------------------------


class LogBugRequest(BaseModel):
    """Request to log a bug."""
    error_type: str = Field(description="Error type, e.g., 'SyntaxError', 'ValueError'.")
    error_message: str = Field(description="Error message.")
    error_traceback: str | None = Field(default=None, description="Full traceback.")
    file_path: str | None = Field(default=None, description="File where the error occurred.")
    line_number: int | None = Field(default=None, description="Line number where the error occurred.")
    context_snippet: str | None = Field(default=None, description="Surrounding code context.")
    metadata: dict | None = Field(default=None, description="Additional metadata.")


class BugResponse(BaseModel):
    """A bug record."""
    id: str
    session_id: str
    agent_id: str | None = None
    error_type: str
    error_message: str
    error_traceback: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    fingerprint: str
    duplicate_of: str | None = None
    status: str
    resolution: str | None = None
    resolved_at: str | None = None
    created_at: str
    updated_at: str


class UpdateBugStatusRequest(BaseModel):
    """Request to update bug status."""
    status: str = Field(description="New status: open, resolved, wont_fix, duplicate.")
    resolution: str | None = Field(default=None, description="Resolution description.")


class BugStatsResponse(BaseModel):
    """Bug statistics."""
    total: int = 0
    open: int = 0
    resolved: int = 0
    duplicates: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cerebrum (Memory)
# ---------------------------------------------------------------------------


class RememberRequest(BaseModel):
    """Request to store a memory."""
    key: str = Field(description="Memory key.")
    value: str = Field(description="Memory value.")
    category: str = Field(default="general", description="Memory category.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0-1).")
    ttl_seconds: int | None = Field(default=None, description="Time-to-live in seconds.")


class MemoryResponse(BaseModel):
    """A memory record."""
    id: str
    key: str
    value: str
    category: str
    confidence: float
    source: str | None = None
    ttl_seconds: int | None = None
    access_count: int = 0
    last_accessed_at: str | None = None
    created_at: str
    updated_at: str


class MemoryStatsResponse(BaseModel):
    """Memory statistics."""
    total_memories: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    total_accesses: int = 0


# ---------------------------------------------------------------------------
# Token Tracking
# ---------------------------------------------------------------------------


class TokenSummaryResponse(BaseModel):
    """Token usage summary."""
    session_id: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_waste_tokens: int = 0
    waste_rate: float = 0.0
    total_cost_usd: float = 0.0
    entry_count: int = 0
    model_breakdown: dict[str, int] = Field(default_factory=dict)
    provider_breakdown: dict[str, int] = Field(default_factory=dict)


class WastePatternResponse(BaseModel):
    """A detected waste pattern."""
    pattern_type: str
    severity: str
    description: str
    tokens_wasted: int
    file_path: str | None = None
    detected_at: str | None = None


# ---------------------------------------------------------------------------
# Context Generation
# ---------------------------------------------------------------------------


class ContextGenerationRequest(BaseModel):
    """Request to generate context string."""
    include_anatomy: bool = True
    include_bugs: bool = True
    include_memory: bool = True
    max_anatomy_entries: int = Field(default=50, ge=1, le=200)
    max_bug_entries: int = Field(default=10, ge=1, le=50)
    max_memory_entries: int = Field(default=50, ge=1, le=200)


class ContextGenerationResponse(BaseModel):
    """Generated context string."""
    context: str = Field(description="The generated context string.")
    estimated_tokens: int = Field(default=0, description="Estimated token count of the context.")


# ---------------------------------------------------------------------------
# Session Summary
# ---------------------------------------------------------------------------


class SessionContextSummaryResponse(BaseModel):
    """Comprehensive session context summary."""
    session_id: str
    agent_id: str | None = None
    created_at: str | None = None
    anatomy: AnatomyStatsResponse | None = None
    bugs: BugStatsResponse | None = None
    memory: MemoryStatsResponse | None = None
    tokens: TokenSummaryResponse | None = None
    waste: dict[str, int] | None = None