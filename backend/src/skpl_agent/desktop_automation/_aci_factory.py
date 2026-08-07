"""ACI factory — creates platform-appropriate ACI instances.

Provides a factory function that creates the correct ACI (Actionable
Context Interface) implementation based on the current platform.
Supports registration of custom ACI implementations for extensibility.

Usage:
    >>> from skpl_agent.desktop_automation._aci_factory import create_aci
    >>> aci = create_aci(top_app_only=True, ocr=False)
    >>> isinstance(aci, ACI)  # True
"""

from __future__ import annotations

import logging
import platform
from typing import Any, Callable

from skpl_agent.desktop_automation._aci import ACI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry of custom ACI implementations
# ---------------------------------------------------------------------------

_custom_aci_registry: dict[str, Callable[..., ACI]] = {}
"""Registry mapping platform names to custom ACI factory callables."""


def register_aci(platform_name: str, factory: Callable[..., ACI]) -> None:
    """Register a custom ACI implementation for a given platform.

    Args:
        platform_name: The platform.system() name (e.g., "Windows", "Linux", "Darwin").
        factory: A callable that accepts ``**kwargs`` and returns an ACI instance.

    Example:
        >>> from skpl_agent.desktop_automation._aci_factory import register_aci
        >>> class MyCustomACI(ACI):
        ...     pass
        >>> register_aci("Windows", lambda **kw: MyCustomACI(**kw))
    """
    _custom_aci_registry[platform_name] = factory
    logger.info("Registered custom ACI for platform: %s", platform_name)


def unregister_aci(platform_name: str) -> bool:
    """Remove a previously registered custom ACI.

    Args:
        platform_name: The platform.system() name.

    Returns:
        True if an ACI was unregistered, False otherwise.
    """
    if platform_name in _custom_aci_registry:
        del _custom_aci_registry[platform_name]
        logger.info("Unregistered custom ACI for platform: %s", platform_name)
        return True
    return False


def list_registered_acis() -> dict[str, str]:
    """Return a dict of registered ACI platforms and their factory names.

    Returns:
        Dict mapping platform name to factory function name.
    """
    return {
        name: factory.__name__ if hasattr(factory, "__name__") else repr(factory)
        for name, factory in _custom_aci_registry.items()
    }


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def _get_platform_name() -> str:
    """Return the current platform.system() name."""
    return platform.system()


def is_platform_supported(platform_name: str | None = None) -> bool:
    """Check if the given (or current) platform has a supported ACI implementation.

    Args:
        platform_name: Platform name to check. If None, uses current platform.

    Returns:
        True if an ACI implementation exists for the platform.
    """
    if platform_name is None:
        platform_name = _get_platform_name()

    if platform_name in _custom_aci_registry:
        return True

    return platform_name in ("Windows", "Darwin", "Linux")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_aci(
    top_app_only: bool = True,
    ocr: bool = False,
    platform_name: str | None = None,
    **kwargs: Any,
) -> ACI:
    """Create an ACI instance appropriate for the current platform.

    Args:
        top_app_only: If True, only extract elements from the foreground app.
        ocr: If True, augment the accessibility tree with OCR-detected text.
        platform_name: Override platform detection. If None, auto-detects.
        **kwargs: Additional keyword arguments passed to the ACI constructor.

    Returns:
        A platform-appropriate ACI instance.

    Raises:
        ImportError: If no ACI implementation is available for the platform.
        ValueError: If the platform name is not recognized.

    Example:
        >>> aci = create_aci(top_app_only=True, ocr=False)
        >>> tree = aci.linearize_and_annotate_tree(obs)
    """
    if platform_name is None:
        platform_name = _get_platform_name()

    logger.info("Creating ACI for platform: %s (top_app_only=%s, ocr=%s)",
                platform_name, top_app_only, ocr)

    # Check for custom ACI first
    if platform_name in _custom_aci_registry:
        factory = _custom_aci_registry[platform_name]
        logger.info("Using custom ACI factory: %s", factory)
        return factory(top_app_only=top_app_only, ocr=ocr, **kwargs)

    # Built-in platform support
    if platform_name == "Windows":
        return _create_windows_aci(top_app_only=top_app_only, ocr=ocr, **kwargs)
    elif platform_name == "Darwin":
        return _create_macos_aci(top_app_only=top_app_only, ocr=ocr, **kwargs)
    elif platform_name == "Linux":
        return _create_linux_aci(top_app_only=top_app_only, ocr=ocr, **kwargs)
    else:
        raise ValueError(
            f"Unsupported platform: {platform_name}. "
            f"Supported platforms: Windows, Darwin, Linux. "
            f"Use register_aci() to add custom platform support."
        )


def create_aci_from_environment(
    top_app_only: bool = True,
    ocr: bool = False,
    **kwargs: Any,
) -> ACI:
    """Create an ACI instance, checking environment variables for overrides.

    Environment variables:
        SKPL_ACI_PLATFORM: Override platform detection.
        SKPL_ACI_TOP_APP_ONLY: Set to "0" or "false" to disable top_app_only.
        SKPL_ACI_OCR: Set to "1" or "true" to enable OCR augmentation.

    Args:
        top_app_only: Default top_app_only value.
        ocr: Default ocr value.
        **kwargs: Additional keyword arguments.

    Returns:
        A platform-appropriate ACI instance.
    """
    import os

    platform_override = os.environ.get("SKPL_ACI_PLATFORM", "").strip()

    top_app_env = os.environ.get("SKPL_ACI_TOP_APP_ONLY", "").strip().lower()
    if top_app_env in ("0", "false", "no"):
        top_app_only = False

    ocr_env = os.environ.get("SKPL_ACI_OCR", "").strip().lower()
    if ocr_env in ("1", "true", "yes"):
        ocr = True

    return create_aci(
        top_app_only=top_app_only,
        ocr=ocr,
        platform_name=platform_override or None,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Internal platform-specific factory helpers
# ---------------------------------------------------------------------------

def _create_windows_aci(
    top_app_only: bool = True,
    ocr: bool = False,
    **kwargs: Any,
) -> ACI:
    """Create a WindowsACI instance."""
    try:
        from skpl_agent.desktop_automation._windows_aci import WindowsACI
        return WindowsACI(top_app_only=top_app_only, ocr=ocr)
    except ImportError as e:
        logger.error("Failed to import WindowsACI: %s", e)
        raise ImportError(
            "WindowsACI requires Windows platform with pywinauto installed. "
            "Install with: pip install pywinauto pywin32"
        ) from e


def _create_macos_aci(
    top_app_only: bool = True,
    ocr: bool = False,
    **kwargs: Any,
) -> ACI:
    """Create a MacOSACI instance."""
    try:
        from skpl_agent.desktop_automation._macos_aci import MacOSACI
        return MacOSACI(top_app_only=top_app_only, ocr=ocr)
    except ImportError as e:
        logger.error("Failed to import MacOSACI: %s", e)
        raise ImportError(
            "MacOSACI requires macOS platform with pyobjc installed. "
            "Install with: pip install pyobjc-framework-Quartz "
            "pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices"
        ) from e


def _create_linux_aci(
    top_app_only: bool = True,
    ocr: bool = False,
    **kwargs: Any,
) -> ACI:
    """Create a LinuxOSACI instance."""
    try:
        from skpl_agent.desktop_automation._linux_aci import LinuxOSACI
        return LinuxOSACI(top_app_only=top_app_only, ocr=ocr)
    except ImportError as e:
        logger.error("Failed to import LinuxOSACI: %s", e)
        raise ImportError(
            "LinuxOSACI requires Linux platform with pyatspi installed. "
            "Install with: pip install pyatspi"
        ) from e


# ---------------------------------------------------------------------------
# ACI capabilities check
# ---------------------------------------------------------------------------

def get_aci_capabilities(platform_name: str | None = None) -> dict[str, Any]:
    """Return the capabilities of the ACI implementation for the given platform.

    Args:
        platform_name: Platform name. If None, uses current platform.

    Returns:
        Dict of capabilities including supported action types and features.
    """
    if platform_name is None:
        platform_name = _get_platform_name()

    base_capabilities: dict[str, Any] = {
        "platform": platform_name,
        "supported": is_platform_supported(platform_name),
        "actions": [
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
        ],
        "features": {
            "accessibility_tree": True,
            "ocr_augmentation": True,
            "screenshot": True,
            "window_management": platform_name == "Linux",
        },
    }

    if platform_name == "Windows":
        base_capabilities["features"]["uia_backend"] = True
        base_capabilities["features"]["desktop_scope"] = True
    elif platform_name == "Darwin":
        base_capabilities["features"]["quartz_screenshot"] = True
        base_capabilities["features"]["ns_workspace"] = True
    elif platform_name == "Linux":
        base_capabilities["features"]["at_spi"] = True
        base_capabilities["features"]["xdotool"] = True
        base_capabilities["actions"].extend(["focus_window", "move_window", "resize_window"])

    return base_capabilities