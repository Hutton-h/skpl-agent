"""UI tree extractor — extract accessibility tree and find UI elements.

Provides UI accessibility tree extraction and element lookup using
platform-specific accessibility APIs. On Windows, uses UI Automation
(UIA) via comtypes/pywinauto. All platform-dependent imports are
lazy-loaded.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """A single UI element from the accessibility tree.

    Attributes:
        element_id: Unique identifier for this element.
        role: Accessibility role (e.g., 'button', 'textbox', 'window').
        name: Accessible name or label of the element.
        value: Current value of the element (if applicable).
        description: Accessibility description.
        class_name: Underlying UI class name.
        rect: (left, top, right, bottom) pixel coordinates.
        is_enabled: Whether the element is enabled.
        is_focused: Whether the element has input focus.
        children: List of child UIElement objects.
        properties: Additional element properties.
    """

    element_id: str = ""
    role: str = ""
    name: str = ""
    value: str = ""
    description: str = ""
    class_name: str = ""
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)
    is_enabled: bool = True
    is_focused: bool = False
    children: list[UIElement] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


class UITreeExtractor:
    """Extracts the UI accessibility tree and finds elements.

    Uses platform-specific accessibility APIs:
    - Windows: UI Automation (UIA) via comtypes/pywinauto
    - macOS: Accessibility API via pyobjc (limited support)
    - Linux: AT-SPI via pyatspi2 (limited support)

    Usage:
        >>> extractor = UITreeExtractor()
        >>> elements = extractor.extract_tree()
        >>> button = extractor.find_element("button", "Submit")
        >>> if button:
        >>>     info = extractor.get_element_info(button.element_id)
    """

    def __init__(self) -> None:
        self._element_registry: dict[str, UIElement] = {}
        self._uia: Optional[object] = None

    # ── Lazy Import ──────────────────────────────────────────────────────

    def _get_uia(self):
        """Lazy-load UI Automation backend."""
        if self._uia is not None:
            return self._uia

        import platform
        system = platform.system()

        if system == "Windows":
            try:
                import comtypes.client
                UIA_dll = comtypes.client.GetModule("UIAutomationCore.dll")
                self._uia = comtypes.client.CreateObject(
                    "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                    interface=UIA_dll.IUIAutomation,
                )
                logger.debug("UI Automation loaded successfully")
                return self._uia
            except ImportError:
                logger.warning(
                    "comtypes not available. Install with: pip install comtypes pywinauto"
                )
                raise
            except OSError as e:
                logger.error("Failed to load UI Automation: %s", e)
                raise
        else:
            raise NotImplementedError(
                f"UI tree extraction is not supported on {system}. "
                "Only Windows (UI Automation) is currently supported."
            )

    # ── Main API ─────────────────────────────────────────────────────────

    def extract_tree(self, max_depth: int = 10) -> list[UIElement]:
        """Extract the full UI accessibility tree.

        Args:
            max_depth: Maximum depth to traverse in the tree.

        Returns:
            List of root-level UIElement objects (typically desktop and
            top-level windows).
        """
        start = time.monotonic()
        self._element_registry.clear()

        try:
            uia = self._get_uia()
            root = uia.GetRootElement()
            tree = self._traverse_element(root, depth=0, max_depth=max_depth)

            elapsed = (time.monotonic() - start) * 1000
            logger.info(
                "UI tree extracted: %d root elements, %d total (%.0fms, depth=%d)",
                len(tree), len(self._element_registry), elapsed, max_depth,
            )
            return tree

        except NotImplementedError:
            logger.warning("UI tree extraction not available on this platform")
            return []
        except Exception as e:
            logger.error("UI tree extraction failed: %s", e)
            return []

    def find_element(
        self,
        role: str = "",
        name: str = "",
    ) -> Optional[UIElement]:
        """Find a UI element by role and/or name.

        Searches the currently extracted tree. Call extract_tree()
        first if stale.

        Args:
            role: Accessibility role to match (case-insensitive).
            name: Accessible name to match (case-insensitive substring).

        Returns:
            Matching UIElement, or None if not found.
        """
        role_lower = role.lower()
        name_lower = name.lower()

        for element in self._element_registry.values():
            role_match = (not role_lower) or (role_lower in element.role.lower())
            name_match = (not name_lower) or (name_lower in element.name.lower())

            if role_match and name_match:
                logger.debug(
                    "Found element: role='%s', name='%s' (id=%s)",
                    element.role, element.name, element.element_id,
                )
                return element

        logger.debug("Element not found: role='%s', name='%s'", role, name)
        return None

    def get_element_info(self, element_id: str) -> Optional[UIElement]:
        """Get detailed information about a UI element by its ID.

        Args:
            element_id: The unique identifier of the element.

        Returns:
            UIElement if found, None otherwise.
        """
        return self._element_registry.get(element_id)

    # ── Internal Traversal ───────────────────────────────────────────────

    def _traverse_element(
        self, uia_element: Any, depth: int, max_depth: int,
    ) -> list[UIElement]:
        """Recursively traverse a UI Automation element tree.

        Args:
            uia_element: The UI Automation element to traverse.
            depth: Current depth in the tree.
            max_depth: Maximum depth to traverse.

        Returns:
            List of UIElement children.
        """
        import uuid

        if depth >= max_depth:
            return []

        children: list[UIElement] = []

        try:
            # Get element properties
            try:
                role = uia_element.CurrentControlType or ""
                name = uia_element.CurrentName or ""
                value = ""
                description = ""
                class_name = uia_element.CurrentClassName or ""
                rect = (
                    uia_element.CurrentBoundingRectangle.left,
                    uia_element.CurrentBoundingRectangle.top,
                    uia_element.CurrentBoundingRectangle.right,
                    uia_element.CurrentBoundingRectangle.bottom,
                )
                is_enabled = bool(uia_element.CurrentIsEnabled)
                is_focused = bool(uia_element.CurrentHasKeyboardFocus)
            except Exception:
                # Element may have become invalid
                return []

            element_id = str(uuid.uuid4())[:8]

            element = UIElement(
                element_id=element_id,
                role=str(role),
                name=name,
                value=value,
                description=description,
                class_name=class_name,
                rect=rect,
                is_enabled=is_enabled,
                is_focused=is_focused,
            )

            self._element_registry[element_id] = element

            # Enumerate children
            try:
                tree_walker = self._uia.CreateTreeWalker(
                    self._uia.RawViewCondition,
                )
                child = tree_walker.GetFirstChildElement(uia_element)
                while child:
                    child_elements = self._traverse_element(
                        child, depth + 1, max_depth,
                    )
                    if child_elements:
                        element.children.extend(child_elements)
                    child = tree_walker.GetNextSiblingElement(child)
            except Exception:
                pass

            children.append(element)

        except Exception as e:
            logger.debug("Element traversal error at depth %d: %s", depth, e)

        return children

    def find_elements(
        self,
        role: str = "",
        name: str = "",
        class_name: str = "",
    ) -> list[UIElement]:
        """Find all UI elements matching the given criteria.

        Args:
            role: Accessibility role to match (case-insensitive).
            name: Accessible name to match (case-insensitive substring).
            class_name: UI class name to match (case-insensitive).

        Returns:
            List of matching UIElements.
        """
        role_lower = role.lower()
        name_lower = name.lower()
        class_lower = class_name.lower()

        results: list[UIElement] = []

        for element in self._element_registry.values():
            role_match = (not role_lower) or (role_lower in element.role.lower())
            name_match = (not name_lower) or (name_lower in element.name.lower())
            class_match = (not class_lower) or (class_lower in element.class_name.lower())

            if role_match and name_match and class_match:
                results.append(element)

        logger.debug(
            "Found %d elements matching: role='%s', name='%s', class='%s'",
            len(results), role, name, class_name,
        )
        return results

    @property
    def element_count(self) -> int:
        """Total number of elements in the current tree."""
        return len(self._element_registry)