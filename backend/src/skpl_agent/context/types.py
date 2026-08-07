"""Context types — Pydantic data models for the context management subsystem.

Defines the canonical data shapes used across anatomy scanning, token tracking,
bug logging, lifecycle hooks, and session context management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Anatomy Types
# ---------------------------------------------------------------------------


class ScanMode(str, Enum):
    """Scan granularity for anatomy extraction."""

    QUICK = "quick"       # Top-level symbols only
    FULL = "full"         # Full symbol tree
    INCREMENTAL = "incremental"  # Changed files only


class SymbolKind(str, Enum):
    """Symbol kind classification."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    MODULE = "module"
    INTERFACE = "interface"
    TYPE = "type"
    ENUM = "enum"
    CONSTANT = "constant"
    DECORATOR = "decorator"
    UNKNOWN = "unknown"


class FileType(str, Enum):
    """Supported file types for anatomy scanning."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    BASH = "bash"
    UNKNOWN = "unknown"


class Symbol(BaseModel):
    """A single extracted symbol from source code."""

    name: str
    kind: SymbolKind
    line: int = 0
    column: int = 0
    end_line: int | None = None
    signature: str | None = None
    description: str | None = None
    parent: str | None = None
    file_path: str = ""
    language: FileType = FileType.UNKNOWN
    docstring: str | None = None
    decorators: list[str] = Field(default_factory=list)
    children: list[Symbol] = Field(default_factory=list)

    @computed_field
    @property
    def full_name(self) -> str:
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name


class ScanOptions(BaseModel):
    """Configuration for anatomy scanning."""

    mode: ScanMode = ScanMode.FULL
    max_depth: int = Field(default=10, ge=1, le=20)
    max_files: int = Field(default=500, ge=1, le=5000)
    max_symbols_per_file: int = Field(default=200, ge=1, le=1000)
    include_docstrings: bool = True
    include_bodies: bool = False
    include_tests: bool = False
    include_hidden: bool = False
    ignore_patterns: list[str] = Field(default_factory=list)
    file_types: list[FileType] | None = None
    parallel: bool = True


class ScanResult(BaseModel):
    """Result of an anatomy scan."""

    project_root: str
    scan_mode: ScanMode
    total_files: int = 0
    scanned_files: int = 0
    total_symbols: int = 0
    total_lines: int = 0
    symbols: list[Symbol] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    @computed_field
    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.scanned_files / self.total_files


class FileHash(BaseModel):
    """Hash of a single file for change detection."""

    path: str
    sha256: str
    size: int = 0
    modified_at: datetime | None = None


# ---------------------------------------------------------------------------
# Token Types
# ---------------------------------------------------------------------------


class TokenCategory(str, Enum):
    """Category of token usage."""

    SYSTEM_PROMPT = "system_prompt"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CONTEXT_INJECTION = "context_injection"
    MEMORY = "memory"
    RAG_RESULT = "rag_result"
    OTHER = "other"


class TokenEntry(BaseModel):
    """A single token consumption record."""

    id: str
    session_id: str
    agent_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    category: TokenCategory = TokenCategory.OTHER
    model_name: str | None = None
    provider: str | None = None
    estimated_cost_usd: float | None = None
    token_budget: int | None = None
    is_waste: bool = False
    waste_reason: str | None = None
    waste_pattern: str | None = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class TokenLedgerSummary(BaseModel):
    """Aggregated token usage summary."""

    session_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_waste_tokens: int = 0
    waste_rate: float = 0.0
    total_cost_usd: float = 0.0
    entry_count: int = 0
    budget_remaining: int | None = None
    budget_percent: float | None = None


class TokenBudget(BaseModel):
    """Token budget configuration."""

    max_tokens: int
    warning_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    hard_limit: bool = True
    per_session: bool = True
    per_agent: bool = False


# ---------------------------------------------------------------------------
# Bug Types
# ---------------------------------------------------------------------------


class BugStatus(str, Enum):
    """Bug tracking status."""

    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


class BugSeverity(str, Enum):
    """Bug severity level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BugRecord(BaseModel):
    """A tracked bug/error from agent execution."""

    id: str
    session_id: str
    agent_id: str | None = None
    error_type: str
    error_message: str
    stack_trace: str | None = None
    severity: BugSeverity = BugSeverity.MEDIUM
    status: BugStatus = BugStatus.NEW
    fingerprint: str | None = None
    occurrence_count: int = 1
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    context_snapshot: str | None = None
    tags: list[str] = Field(default_factory=list)


class BugDeduplicationResult(BaseModel):
    """Result of bug deduplication using Jaccard similarity."""

    is_duplicate: bool
    similarity: float = 0.0
    matched_bug_id: str | None = None
    matched_fingerprint: str | None = None


# ---------------------------------------------------------------------------
# Lifecycle Types
# ---------------------------------------------------------------------------


class LifecyclePhase(str, Enum):
    """Phase in the agent lifecycle where a hook executes."""

    ON_SESSION_START = "on_session_start"
    BEFORE_AGENT_INVOKE = "before_agent_invoke"
    AFTER_AGENT_INVOKE = "after_agent_invoke"
    ON_TOOL_CALL = "on_tool_call"
    ON_TOOL_RESULT = "on_tool_result"
    ON_ERROR = "on_error"
    ON_SESSION_END = "on_session_end"


class HookContext(BaseModel):
    """Context passed to lifecycle hooks."""

    session_id: str
    agent_id: str | None = None
    phase: LifecyclePhase
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)


class HookResult(BaseModel):
    """Result returned by a lifecycle hook."""

    hook_name: str
    phase: LifecyclePhase
    success: bool
    injected_context: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session Context Types
# ---------------------------------------------------------------------------


class SessionContextConfig(BaseModel):
    """Configuration for session-level context management."""

    max_context_tokens: int = Field(default=32000, ge=1000)
    anatomy_injection: bool = True
    token_tracking: bool = True
    bug_logging: bool = True
    waste_detection: bool = True
    sensitive_filter: bool = True
    fallback_strategy: bool = True
    cache_anatomy: bool = True
    max_file_context: int = Field(default=50, ge=1, le=500)


class SessionContext(BaseModel):
    """Aggregated context for a session."""

    session_id: str
    project_root: str | None = None
    anatomy_summary: str | None = None
    recent_bugs: list[BugRecord] = Field(default_factory=list)
    token_summary: TokenLedgerSummary | None = None
    injected_context: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Sensitive Content Types
# ---------------------------------------------------------------------------


class SensitivePattern(BaseModel):
    """A detected sensitive content pattern."""

    pattern_name: str
    category: str  # "api_key", "password", "token", "pii", "internal_url"
    matched_text: str
    line: int | None = None
    file_path: str | None = None
    severity: BugSeverity = BugSeverity.HIGH
    redacted: bool = False


class SensitiveScanResult(BaseModel):
    """Result of a sensitive content scan."""

    has_sensitive: bool
    pattern_count: int = 0
    patterns: list[SensitivePattern] = Field(default_factory=list)
    scan_duration_ms: float = 0.0


__all__ = [
    # Anatomy
    "ScanMode",
    "ScanOptions",
    "ScanResult",
    "Symbol",
    "SymbolKind",
    "FileType",
    "FileHash",
    # Token
    "TokenCategory",
    "TokenEntry",
    "TokenLedgerSummary",
    "TokenBudget",
    # Bug
    "BugStatus",
    "BugSeverity",
    "BugRecord",
    "BugDeduplicationResult",
    # Lifecycle
    "LifecyclePhase",
    "HookContext",
    "HookResult",
    # Session
    "SessionContextConfig",
    "SessionContext",
    # Security
    "SensitivePattern",
    "SensitiveScanResult",
]