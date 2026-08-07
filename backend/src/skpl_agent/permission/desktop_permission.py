"""Desktop permission rules — access control for desktop automation.

Provides permission rules specifically for desktop automation operations,
including operation whitelists/blacklists, application-level access
control, and sensitive operation confirmation requirements.

Integrates with the SKPL Agent permission system (PermissionRule,
PermissionBehavior, PermissionMode) to provide fine-grained control
over which desktop operations are allowed.
"""

from __future__ import annotations

import logging
from typing import Any

from ..permission._types import PermissionBehavior

logger = logging.getLogger(__name__)


class DesktopPermissionRule:
    """Permission rule for desktop automation operations.

    Controls which desktop operations are allowed for specific applications
    and contexts. Supports whitelists, blacklists, and confirmation
    requirements for sensitive operations.

    Usage:
        >>> rule = DesktopPermissionRule(
        ...     allowed_actions=["click", "type", "screenshot"],
        ...     denied_actions=["open_app", "custom_code"],
        ...     allowed_apps=["notepad.exe", "chrome.exe"],
        ...     require_confirmation_for=["hotkey", "drag"],
        ... )
        >>> rule.is_allowed("click", app="notepad.exe")
        True
        >>> rule.is_allowed("open_app", app="notepad.exe")
        False
    """

    # Sensitive actions that should always require confirmation
    DEFAULT_SENSITIVE_ACTIONS: set[str] = {
        "open_app",
        "switch_app",
        "custom_code",
        "hotkey",
        "drag",
    }

    # Read-only actions that are generally safe
    DEFAULT_READ_ONLY_ACTIONS: set[str] = {
        "screenshot",
        "wait",
    }

    # All known desktop action types
    ALL_KNOWN_ACTIONS: set[str] = {
        "click",
        "double_click",
        "right_click",
        "type",
        "key_press",
        "hotkey",
        "scroll",
        "drag",
        "move",
        "wait",
        "screenshot",
        "open_app",
        "switch_app",
        "custom_code",
    }

    def __init__(
        self,
        allowed_actions: list[str] | None = None,
        denied_actions: list[str] | None = None,
        allowed_apps: list[str] | None = None,
        denied_apps: list[str] | None = None,
        require_confirmation_for: list[str] | None = None,
        allow_all_actions: bool = False,
        deny_all_by_default: bool = False,
    ) -> None:
        self._allowed_actions: set[str] = set(
            allowed_actions or []
        )
        self._denied_actions: set[str] = set(
            denied_actions or []
        )
        self._allowed_apps: set[str] = set(
            a.lower() for a in (allowed_apps or [])
        )
        self._denied_apps: set[str] = set(
            a.lower() for a in (denied_apps or [])
        )
        self._require_confirmation: set[str] = set(
            require_confirmation_for or []
        )
        self._allow_all_actions = allow_all_actions
        self._deny_all_by_default = deny_all_by_default

        # Merge with default sensitive actions
        if not require_confirmation_for:
            self._require_confirmation = self.DEFAULT_SENSITIVE_ACTIONS.copy()

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def allowed_actions(self) -> set[str]:
        """Return the set of explicitly allowed actions."""
        return self._allowed_actions.copy()

    @property
    def denied_actions(self) -> set[str]:
        """Return the set of explicitly denied actions."""
        return self._denied_actions.copy()

    @property
    def allowed_apps(self) -> set[str]:
        """Return the set of allowed application names."""
        return self._allowed_apps.copy()

    @property
    def denied_apps(self) -> set[str]:
        """Return the set of denied application names."""
        return self._denied_apps.copy()

    @property
    def require_confirmation(self) -> set[str]:
        """Return the set of actions requiring confirmation."""
        return self._require_confirmation.copy()

    # ── Rule management ──────────────────────────────────────────────────

    def allow_action(self, action: str) -> None:
        """Add an action to the allowed list.

        Args:
            action: Action name to allow.
        """
        self._allowed_actions.add(action)
        self._denied_actions.discard(action)
        logger.debug("Allowed action: %s", action)

    def deny_action(self, action: str) -> None:
        """Add an action to the denied list.

        Args:
            action: Action name to deny.
        """
        self._denied_actions.add(action)
        self._allowed_actions.discard(action)
        logger.debug("Denied action: %s", action)

    def allow_app(self, app_name: str) -> None:
        """Add an application to the allowed list.

        Args:
            app_name: Application name (case-insensitive).
        """
        self._allowed_apps.add(app_name.lower())
        self._denied_apps.discard(app_name.lower())
        logger.debug("Allowed app: %s", app_name)

    def deny_app(self, app_name: str) -> None:
        """Add an application to the denied list.

        Args:
            app_name: Application name (case-insensitive).
        """
        self._denied_apps.add(app_name.lower())
        self._allowed_apps.discard(app_name.lower())
        logger.debug("Denied app: %s", app_name)

    def require_confirmation_for(self, action: str) -> None:
        """Mark an action as requiring user confirmation.

        Args:
            action: Action name.
        """
        self._require_confirmation.add(action)

    def remove_confirmation_requirement(self, action: str) -> None:
        """Remove confirmation requirement for an action.

        Args:
            action: Action name.
        """
        self._require_confirmation.discard(action)

    # ── Permission checks ────────────────────────────────────────────────

    def is_allowed(
        self,
        action: str,
        app: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Check if an action is allowed.

        Resolution order:
        1. Explicit deny (action or app) -> False
        2. Explicit allow (action or app) -> True
        3. If allow_all_actions -> True
        4. If deny_all_by_default -> False
        5. Default: True (allow by default)

        Args:
            action: The action name (e.g., "click", "type").
            app: Optional application name for app-level checks.
            params: Optional action parameters for context-aware checks.

        Returns:
            True if the action is allowed.
        """
        # Check app-level deny
        if app and app.lower() in self._denied_apps:
            logger.debug("Action '%s' denied: app '%s' is blacklisted", action, app)
            return False

        # Check action-level deny
        if action in self._denied_actions:
            logger.debug("Action '%s' denied: explicitly blacklisted", action)
            return False

        # Check app-level allow
        if app and self._allowed_apps and app.lower() in self._allowed_apps:
            return True

        # Check action-level allow
        if action in self._allowed_actions:
            return True

        # If allow_all_actions is set, allow everything not denied
        if self._allow_all_actions:
            return True

        # If deny_all_by_default, deny everything not explicitly allowed
        if self._deny_all_by_default:
            logger.debug("Action '%s' denied: deny_all_by_default is set", action)
            return False

        # Default: allow
        return True

    def needs_confirmation(
        self,
        action: str,
        app: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Check if an action requires user confirmation.

        Args:
            action: The action name.
            app: Optional application name.
            params: Optional action parameters.

        Returns:
            True if the action requires confirmation.
        """
        return action in self._require_confirmation

    def get_behavior(
        self,
        action: str,
        app: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> PermissionBehavior:
        """Get the permission behavior for an action.

        Args:
            action: The action name.
            app: Optional application name.
            params: Optional action parameters.

        Returns:
            PermissionBehavior.ALLOW, DENY, or ASK.
        """
        if not self.is_allowed(action, app, params):
            return PermissionBehavior.DENY

        if self.needs_confirmation(action, app, params):
            return PermissionBehavior.ASK

        return PermissionBehavior.ALLOW

    def is_read_only(self, action: str) -> bool:
        """Check if an action is read-only (safe to execute without user).

        Args:
            action: The action name.

        Returns:
            True if the action is read-only.
        """
        return action in self.DEFAULT_READ_ONLY_ACTIONS

    def is_sensitive(self, action: str) -> bool:
        """Check if an action is considered sensitive.

        Args:
            action: The action name.

        Returns:
            True if the action is sensitive.
        """
        return action in self.DEFAULT_SENSITIVE_ACTIONS

    # ── Bulk operations ──────────────────────────────────────────────────

    def allow_all(self) -> None:
        """Allow all actions."""
        self._allow_all_actions = True
        self._deny_all_by_default = False
        self._denied_actions.clear()
        logger.info("All actions allowed")

    def deny_all(self) -> None:
        """Deny all actions by default."""
        self._deny_all_by_default = True
        self._allow_all_actions = False
        self._allowed_actions.clear()
        logger.info("All actions denied by default")

    def reset_to_defaults(self) -> None:
        """Reset to default permission settings."""
        self._allowed_actions.clear()
        self._denied_actions.clear()
        self._allowed_apps.clear()
        self._denied_apps.clear()
        self._require_confirmation = self.DEFAULT_SENSITIVE_ACTIONS.copy()
        self._allow_all_actions = False
        self._deny_all_by_default = False
        logger.info("Desktop permission rules reset to defaults")

    def to_dict(self) -> dict[str, Any]:
        """Export the rule configuration as a dict.

        Returns:
            Dict representation of the rule.
        """
        return {
            "allowed_actions": sorted(self._allowed_actions),
            "denied_actions": sorted(self._denied_actions),
            "allowed_apps": sorted(self._allowed_apps),
            "denied_apps": sorted(self._denied_apps),
            "require_confirmation": sorted(self._require_confirmation),
            "allow_all_actions": self._allow_all_actions,
            "deny_all_by_default": self._deny_all_by_default,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DesktopPermissionRule:
        """Create a rule from a dict.

        Args:
            data: Dict with rule configuration.

        Returns:
            DesktopPermissionRule instance.
        """
        return cls(
            allowed_actions=data.get("allowed_actions", []),
            denied_actions=data.get("denied_actions", []),
            allowed_apps=data.get("allowed_apps", []),
            denied_apps=data.get("denied_apps", []),
            require_confirmation_for=data.get("require_confirmation", []),
            allow_all_actions=data.get("allow_all_actions", False),
            deny_all_by_default=data.get("deny_all_by_default", False),
        )

    @classmethod
    def create_permissive(cls) -> DesktopPermissionRule:
        """Create a permissive rule that allows all actions.

        Returns:
            DesktopPermissionRule with all actions allowed.
        """
        return cls(allow_all_actions=True)

    @classmethod
    def create_strict(cls) -> DesktopPermissionRule:
        """Create a strict rule that only allows read-only actions.

        Returns:
            DesktopPermissionRule with strict settings.
        """
        return cls(
            allowed_actions=list(cls.DEFAULT_READ_ONLY_ACTIONS),
            denied_actions=list(
                cls.ALL_KNOWN_ACTIONS - cls.DEFAULT_READ_ONLY_ACTIONS
            ),
            deny_all_by_default=True,
        )

    @classmethod
    def create_safe_default(cls) -> DesktopPermissionRule:
        """Create a safe default rule with sensible defaults.

        Allows common actions but requires confirmation for sensitive
        operations like opening apps or running custom code.

        Returns:
            DesktopPermissionRule with safe defaults.
        """
        rule = cls()
        rule._denied_actions = {"custom_code"}
        return rule

    def __repr__(self) -> str:
        return (
            f"DesktopPermissionRule("
            f"allowed={len(self._allowed_actions)}, "
            f"denied={len(self._denied_actions)}, "
            f"apps_allowed={len(self._allowed_apps)}, "
            f"apps_denied={len(self._denied_apps)}, "
            f"confirm={len(self._require_confirmation)}, "
            f"allow_all={self._allow_all_actions}, "
            f"deny_all={self._deny_all_by_default})"
        )