"""The permission decision result."""
from dataclasses import dataclass
from typing import Any
from ._rule import PermissionRule
from ._types import PermissionBehavior

@dataclass
class PermissionDecision:
    """Decision result from permission checking.

    Represents the outcome of a permission check, including whether
    the action should be allowed, denied, or require user confirmation.
    """
    behavior: PermissionBehavior
    'The permission behavior decision.'
    message: str
    'Human-readable message describing the decision.'
    decision_reason: str | None = None
    'Optional explanation for why this decision was made.'
    updated_input: dict[str, Any] | None = None
    'Optional modified input data (e.g., sanitized paths).'
    suggested_rules: list[PermissionRule] | None = None
    'Optional list of suggested permission rules for user to apply.'
    bypass_immune: bool = False
    'Whether this decision is immune to being silenced by allow rules\n    ("bypass-immune").\n\n    Only meaningful when :attr:`behavior` is :attr:`PermissionBehavior.ASK`.\n    A tool sets this to ``True`` to signal that the operation is\n    dangerous enough that **no allow rule** may convert the ASK into an\n    ALLOW — the user must explicitly confirm in-the-moment. In\n    :attr:`PermissionMode.DONT_ASK` where no user is available, a\n    bypass-immune ASK is converted to DENY rather than silently allowed.\n\n    Per-mode handling of a ``bypass_immune=True`` ASK:\n\n    - ``DEFAULT`` / ``ACCEPT_EDITS``: honored — allow rules cannot\n      override.\n    - ``EXPLORE``: not applicable (the engine resolves EXPLORE via\n      :meth:`ToolBase.check_read_only` and does not invoke\n      :meth:`ToolBase.check_permissions`).\n    - ``BYPASS``: **intentionally ignored** — BYPASS\'s contract is\n      "the user has opted out of safety prompts; only deny / ask\n      rules remain as guardrails." Use deny rules in BYPASS to\n      enforce specific protections.\n    - ``DONT_ASK``: converted to DENY (no user available).\n\n    Default is ``False``: a regular ASK that may be overridden by an\n    allow rule in DEFAULT / ACCEPT_EDITS, and is silently allowed by\n    BYPASS\'s fallback. Tools should set this only for genuine safety\n    checks (e.g. writes to dangerous paths, ``rm -rf /``, command\n    injection patterns) — not for "I\'d prefer user input" cases.\n\n    Note: this field is internal metadata for the permission engine.\n    Callers handling the decision (agent loop, HITL backend, UI) treat\n    a bypass-immune ASK the same as a regular ASK — both prompt the\n    user. The distinction only governs whether engine-level rules /\n    modes may override it before reaching the caller.\n    '