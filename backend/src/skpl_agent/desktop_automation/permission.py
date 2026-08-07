"""Desktop permission — access control for desktop automation operations.

Provides permission checking for desktop automation actions:
- PermissionBehavior: enum defining how permissions are handled
- PermissionContext: context for permission evaluation
- PermissionDecision: result of a permission check

Integrates with the desktop tool to enforce security policies
before executing automation operations on remote machines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionBehavior(Enum):
    """How a permission check should behave."""

    ALLOW = "allow"          # Always allow
    DENY = "deny"            # Always deny
    ASK = "ask"              # Ask the user for confirmation
    LOG_ONLY = "log_only"    # Allow but log the operation


class PermissionDecision(Enum):
    """Result of a permission check."""

    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"      # Waiting for user confirmation


@dataclass
class PermissionContext:
    """Context for evaluating a desktop automation permission.

    Captures all relevant information about the operation being
    requested, including the action type, target, and requester.
    """

    action: str
    """The desktop action being requested (click, type, screenshot, etc.)."""

    node_id: str | None = None
    """The desktop node where the action will execute."""

    session_id: str | None = None
    """The agent session requesting the action."""

    agent_id: str | None = None
    """The agent making the request."""

    # Screen coordinates for click/move actions
    x: int | None = None
    y: int | None = None

    # Key details for keyboard actions
    keys: list[str] | None = None
    text: str | None = None

    # Screenshot parameters
    include_sensitive: bool = False

    # Arbitrary metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for logging."""
        return {
            "action": self.action,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "x": self.x,
            "y": self.y,
            "keys": self.keys,
            "text": self.text[:100] if self.text else None,
            "include_sensitive": self.include_sensitive,
        }


class DesktopPermission:
    """Manages desktop automation permissions.

    Determines whether a desktop automation action is allowed based
    on configured policies. Supports per-action, per-node, and
    per-session permission rules.

    Usage:
        >>> perm = DesktopPermission(default_behavior=PermissionBehavior.LOG_ONLY)
        >>> ctx = PermissionContext(action="click", node_id="node-1")
        >>> decision = perm.check(ctx)
        >>> if decision == PermissionDecision.GRANTED:
        ...     await execute_action()
    """

    def __init__(
        self,
        default_behavior: PermissionBehavior = PermissionBehavior.ASK,
        allowed_actions: set[str] | None = None,
        denied_actions: set[str] | None = None,
        allowed_nodes: set[str] | None = None,
        require_approval_for: set[str] | None = None,
    ) -> None:
        self._default_behavior = default_behavior
        self._allowed_actions = allowed_actions or set()
        self._denied_actions = denied_actions or set()
        self._allowed_nodes = allowed_nodes or set()
        self._require_approval_for = require_approval_for or set()
        self._history: list[PermissionContext] = []

    @property
    def default_behavior(self) -> PermissionBehavior:
        return self._default_behavior

    def check(self, ctx: PermissionContext) -> PermissionDecision:
        """Check if an action is permitted.

        Evaluates in order:
        1. If the action is explicitly denied → DENIED
        2. If the node is restricted and not in the allowed set → DENIED
        3. If the action is explicitly allowed → GRANTED
        4. If the action requires approval → PENDING
        5. Otherwise → depends on default behavior

        Returns:
            PermissionDecision: GRANTED, DENIED, or PENDING.
        """
        self._history.append(ctx)

        # 1. Explicit deny
        if ctx.action in self._denied_actions:
            return PermissionDecision.DENIED

        # 2. Node restriction
        if self._allowed_nodes and ctx.node_id not in self._allowed_nodes:
            return PermissionDecision.DENIED

        # 3. Explicit allow
        if ctx.action in self._allowed_actions:
            return PermissionDecision.GRANTED

        # 4. Require approval
        if ctx.action in self._require_approval_for:
            return PermissionDecision.PENDING

        # 5. Default behavior
        if self._default_behavior == PermissionBehavior.ALLOW:
            return PermissionDecision.GRANTED
        elif self._default_behavior == PermissionBehavior.DENY:
            return PermissionDecision.DENIED
        elif self._default_behavior == PermissionBehavior.ASK:
            return PermissionDecision.PENDING
        elif self._default_behavior == PermissionBehavior.LOG_ONLY:
            return PermissionDecision.GRANTED

        return PermissionDecision.DENIED

    def allow_action(self, action: str) -> None:
        """Add an action to the allowed set."""
        self._allowed_actions.add(action)
        self._denied_actions.discard(action)

    def deny_action(self, action: str) -> None:
        """Add an action to the denied set."""
        self._denied_actions.add(action)
        self._allowed_actions.discard(action)

    def allow_node(self, node_id: str) -> None:
        """Add a node to the allowed set."""
        self._allowed_nodes.add(node_id)

    def require_approval(self, action: str) -> None:
        """Mark an action as requiring user approval."""
        self._require_approval_for.add(action)

    def get_history(self, limit: int = 50) -> list[PermissionContext]:
        """Get recent permission check history."""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear permission check history."""
        self._history.clear()

    def get_policy(self) -> dict[str, Any]:
        """Get the current permission policy configuration."""
        return {
            "default_behavior": self._default_behavior.value,
            "allowed_actions": sorted(self._allowed_actions),
            "denied_actions": sorted(self._denied_actions),
            "allowed_nodes": sorted(self._allowed_nodes),
            "require_approval_for": sorted(self._require_approval_for),
            "total_checks": len(self._history),
        }


# Default permission instance for quick use
_default_permission = DesktopPermission()


def get_default_permission() -> DesktopPermission:
    """Get the default desktop permission instance."""
    return _default_permission