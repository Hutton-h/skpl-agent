"""SKPL Agent Context Management (OpenWolf Integration).

Provides automated context management for agent sessions:
- Anatomy scanning: Extract symbols and descriptions from project codebases
- Token management: Track token usage with waste detection
- BugLog: Error tracking with Jaccard deduplication
- Cerebrum: Agent "brain" state persistence
- Lifecycle hooks: 7 hooks for context injection into agent sessions
- Sensitive filter: Detect and sanitize sensitive content
- External adapters: Integrate with Claude Code, Codex, Cursor
"""

from skpl_agent.context.anatomy_lock import AnatomyLock, NoOpLock
from skpl_agent.context.anatomy_scanner import (
    AnatomyScanner,
    ScanMode,
    ScanOptions,
    ScanResult,
    compute_file_hash,
    compute_source_hash,
)
from skpl_agent.context.anatomy_store import AnatomyStore, AnatomyStoreMode
from skpl_agent.context.bug_matcher import BugMatcher
from skpl_agent.context.buglog import BugLog, BugRecord, BugStatus
from skpl_agent.context.cerebrum import Cerebrum, Memory
from skpl_agent.context.lifecycle import (
    ContextLifecycle,
    HookContext,
    LifecycleHook,
    OnSessionStartHook,
    BeforeAgentInvokeHook,
    AfterAgentInvokeHook,
    OnToolCallHook,
    OnToolResultHook,
    OnErrorHook,
    OnSessionEndHook,
)
from skpl_agent.context.sensitive_filter import SensitiveContentFilter, SensitiveScanResult
from skpl_agent.context.session_context import SessionContextConfig, SessionContextManager
from skpl_agent.context.symbol_extractor import (
    DescriptionExtractor,
    Symbol,
    SymbolExtractor,
    detect_language,
)
from skpl_agent.context.token_estimator import (
    TokenEstimator,
    estimate_tokens,
    estimate_file_tokens,
)
from skpl_agent.context.token_ledger import (
    BudgetExceededError,
    TokenEntry,
    TokenLedger,
    TokenLedgerSummary,
)
from skpl_agent.context.waste_detector import WasteDetector, WastePattern
from skpl_agent.context.event_emitter import ContextEventEmitter
from skpl_agent.context.fallback import (
    CommentsExtractor,
    ContextFallbackStrategy,
    FallbackContext,
    FallbackResult,
    FileHeuristicScanner,
)
from skpl_agent.context.types import (
    BugDeduplicationResult,
    BugSeverity,
    FileHash,
    FileType,
    HookResult,
    LifecyclePhase,
    ScanMode as ScanModeType,
    SensitivePattern,
    SessionContext,
    SymbolKind,
    TokenBudget,
    TokenCategory,
)

__all__ = [
    # Anatomy
    "AnatomyLock",
    "NoOpLock",
    "AnatomyScanner",
    "ScanMode",
    "ScanOptions",
    "ScanResult",
    "compute_file_hash",
    "compute_source_hash",
    "AnatomyStore",
    "AnatomyStoreMode",
    # Symbol extraction
    "Symbol",
    "SymbolExtractor",
    "DescriptionExtractor",
    "detect_language",
    # Token management
    "TokenEstimator",
    "TokenLedger",
    "TokenEntry",
    "TokenLedgerSummary",
    "BudgetExceededError",
    "estimate_tokens",
    "estimate_file_tokens",
    # Waste detection
    "WasteDetector",
    "WastePattern",
    # Bug tracking
    "BugLog",
    "BugRecord",
    "BugStatus",
    "BugMatcher",
    # Memory
    "Cerebrum",
    "Memory",
    # Lifecycle
    "ContextLifecycle",
    "LifecycleHook",
    "HookContext",
    "OnSessionStartHook",
    "BeforeAgentInvokeHook",
    "AfterAgentInvokeHook",
    "OnToolCallHook",
    "OnToolResultHook",
    "OnErrorHook",
    "OnSessionEndHook",
    # Session
    "SessionContextManager",
    "SessionContextConfig",
    # Security
    "SensitiveContentFilter",
    "SensitiveScanResult",
    # Event emitter
    "ContextEventEmitter",
    # Fallback
    "ContextFallbackStrategy",
    "FallbackContext",
    "FallbackResult",
    "FileHeuristicScanner",
    "CommentsExtractor",
    # Types (Pydantic models)
    "BugDeduplicationResult",
    "BugSeverity",
    "FileHash",
    "FileType",
    "HookResult",
    "LifecyclePhase",
    "ScanModeType",
    "SensitivePattern",
    "SessionContext",
    "SymbolKind",
    "TokenBudget",
    "TokenCategory",
]