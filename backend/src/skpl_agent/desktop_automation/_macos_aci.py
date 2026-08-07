"""macOS ACI implementation — Accessibility API via pyobjc.

Implements the ACI (Actionable Context Interface) for macOS using the
system Accessibility API through pyobjc. Provides UI tree extraction,
screenshot capture, and action code generation for desktop automation.

Note: Platform-specific imports (pyobjc, Cocoa, Quartz) are lazy-loaded
to allow the module to be imported on non-macOS systems for type checking.
"""

from __future__ import annotations

import base64
import io
import logging
import platform
from typing import Any

from skpl_agent.desktop_automation._aci import ACI, agent_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy platform helpers
# ---------------------------------------------------------------------------

_pyautogui: Any = None
_Quartz: Any = None
_Cocoa: Any = None
_AppKit: Any = None
_psutil: Any = None


def _ensure_macos_imports() -> None:
    """Lazy-import macOS-specific modules. Raises ImportError on non-macOS."""
    global _pyautogui, _Quartz, _Cocoa, _AppKit, _psutil
    if _AppKit is not None:
        return
    if platform.system() != "Darwin":
        raise ImportError("MacOSACI requires macOS platform")

    import pyautogui as _pyautogui
    import psutil as _psutil

    try:
        import Quartz as _Quartz
        import Cocoa as _Cocoa
        import AppKit as _AppKit
    except ImportError as e:
        raise ImportError(
            "pyobjc not installed. Install with: pip install pyobjc-framework-Quartz "
            "pyobjc-framework-Cocoa pyobjc-framework-ApplicationServices"
        ) from e


def _normalize_key(key: str) -> str:
    """Convert key names for pyautogui compatibility."""
    key_map: dict[str, str] = {
        "command": "command",
        "cmd": "command",
        "option": "option",
        "alt": "option",
        "control": "ctrl",
        "ctrl": "ctrl",
        "shift": "shift",
        "capslock": "capslock",
        "tab": "tab",
        "enter": "enter",
        "return": "enter",
        "escape": "esc",
        "esc": "esc",
        "delete": "backspace",
        "backspace": "backspace",
        "space": "space",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "home": "home",
        "end": "end",
        "pageup": "pageup",
        "pagedown": "pagedown",
    }
    return key_map.get(key.lower(), key)


# ---------------------------------------------------------------------------
# UIElement — macOS-specific element wrapper
# ---------------------------------------------------------------------------

class MacUIElement:
    """Wrapper around a macOS accessibility element (AXUIElement).

    Provides safe attribute access and tree traversal for UI elements
    obtained via the macOS Accessibility API.
    """

    def __init__(self, element: Any = None) -> None:
        _ensure_macos_imports()
        self._element = element
        self._attrs_cache: dict[str, Any] = {}

    def _get_attr(self, name: str) -> Any:
        """Get an accessibility attribute, with caching."""
        if name in self._attrs_cache:
            return self._attrs_cache[name]
        try:
            err, value = _Quartz.AXUIElementCopyAttributeValue(
                self._element, name, None
            )
            if err == 0:  # kAXErrorSuccess
                self._attrs_cache[name] = value
                return value
        except Exception:
            pass
        return None

    def _get_attr_names(self) -> list[str]:
        """Get all available attribute names for this element."""
        try:
            err, names = _Quartz.AXUIElementCopyAttributeNames(
                self._element, None
            )
            if err == 0 and names:
                return list(names)
        except Exception:
            pass
        return []

    def role(self) -> str:
        """Return the AXRole of this element."""
        val = self._get_attr("AXRole")
        return str(val) if val else "Unknown"

    def subrole(self) -> str:
        """Return the AXSubrole of this element."""
        val = self._get_attr("AXSubrole")
        return str(val) if val else ""

    def title(self) -> str:
        """Return the AXTitle."""
        val = self._get_attr("AXTitle")
        return str(val) if val else ""

    def description(self) -> str:
        """Return the AXDescription."""
        val = self._get_attr("AXDescription")
        return str(val) if val else ""

    def value(self) -> str:
        """Return the AXValue."""
        val = self._get_attr("AXValue")
        return str(val) if val else ""

    def position(self) -> tuple[int, int] | None:
        """Return the (x, y) position of this element."""
        val = self._get_attr("AXPosition")
        if val is not None:
            try:
                point = _Quartz.CGPointMake(0, 0)
                _Quartz.AXValueGetValue(val, _Quartz.kAXValueCGPointType, point)
                return (int(point.x), int(point.y))
            except Exception:
                pass
        return None

    def size(self) -> tuple[int, int] | None:
        """Return the (width, height) of this element."""
        val = self._get_attr("AXSize")
        if val is not None:
            try:
                size = _Quartz.CGSizeMake(0, 0)
                _Quartz.AXValueGetValue(val, _Quartz.kAXValueCGSizeType, size)
                return (int(size.width), int(size.height))
            except Exception:
                pass
        return None

    def children(self) -> list[MacUIElement]:
        """Return the children of this element."""
        val = self._get_attr("AXChildren")
        if val is not None:
            try:
                count = _Quartz.CFArrayGetCount(val)
                result: list[MacUIElement] = []
                for i in range(count):
                    child = _Quartz.CFArrayGetValueAtIndex(val, i)
                    if child:
                        result.append(MacUIElement(child))
                return result
            except Exception:
                pass
        return []

    def is_enabled(self) -> bool:
        """Check if the element is enabled."""
        val = self._get_attr("AXEnabled")
        return bool(val)

    def is_focused(self) -> bool:
        """Check if the element is focused."""
        val = self._get_attr("AXFocused")
        return bool(val)

    def parent(self) -> MacUIElement | None:
        """Return the parent of this element."""
        val = self._get_attr("AXParent")
        if val:
            return MacUIElement(val)
        return None

    def parse(self) -> dict[str, Any]:
        """Return a dict representation of this element."""
        pos = self.position()
        sz = self.size()
        return {
            "position": pos,
            "size": sz,
            "title": self.title(),
            "description": self.description(),
            "value": self.value(),
            "role": self.role(),
            "subrole": self.subrole(),
            "enabled": self.is_enabled(),
        }

    def is_valid(self) -> bool:
        """Check if the element has valid position and size."""
        pos = self.position()
        sz = self.size()
        return (
            pos is not None
            and sz is not None
            and pos[0] >= 0
            and pos[1] >= 0
            and sz[0] > 0
            and sz[1] > 0
        )

    @staticmethod
    def system_wide_element() -> MacUIElement:
        """Return the system-wide accessibility element."""
        _ensure_macos_imports()
        ax_system = _Quartz.AXUIElementCreateSystemWide()
        return MacUIElement(ax_system)

    @staticmethod
    def focused_application() -> MacUIElement | None:
        """Return the accessibility element for the focused application."""
        _ensure_macos_imports()
        sys_wide = _Quartz.AXUIElementCreateSystemWide()
        err, app = _Quartz.AXUIElementCopyAttributeValue(
            sys_wide, "AXFocusedApplication", None
        )
        if err == 0 and app:
            return MacUIElement(app)
        return None

    @staticmethod
    def get_running_applications() -> list[dict[str, Any]]:
        """Return a list of running applications with basic info."""
        _ensure_macos_imports()
        apps: list[dict[str, Any]] = []
        try:
            workspace = _AppKit.NSWorkspace.sharedWorkspace()
            running = workspace.runningApplications()
            for app in running:
                if app.activationPolicy() == 0:  # NSApplicationActivationPolicyRegular
                    apps.append({
                        "name": str(app.localizedName()) if app.localizedName() else "",
                        "bundle_id": str(app.bundleIdentifier()) if app.bundleIdentifier() else "",
                        "pid": app.processIdentifier(),
                    })
        except Exception as e:
            logger.warning("Failed to list running applications: %s", e)
        return apps

    def __repr__(self) -> str:
        return f"MacUIElement(role={self.role()!r}, title={self.title()!r})"


# ---------------------------------------------------------------------------
# MacOSACI
# ---------------------------------------------------------------------------

class MacOSACI(ACI):
    """macOS desktop automation via Accessibility API + pyautogui.

    Extracts the UI element tree from the focused application, optionally
    augments it with OCR, and generates pyautogui code strings for each
    action (click, type, scroll, hotkey, etc.).

    Usage:
        >>> aci = MacOSACI(top_app_only=True, ocr=False)
        >>> obs = {"screenshot": b"..."}
        >>> tree_text = aci.linearize_and_annotate_tree(obs)
        >>> code = aci.click(element_id=3)
        >>> exec(code)
    """

    def __init__(self, top_app_only: bool = True, ocr: bool = False) -> None:
        super().__init__(top_app_only=top_app_only, ocr=ocr)
        _ensure_macos_imports()
        self._screen_size: tuple[int, int] | None = None

    # ── Screenshot ───────────────────────────────────────────────────────

    def capture_screenshot(
        self,
        region: tuple[int, int, int, int] | None = None,
        img_format: str = "jpeg",
        quality: int = 85,
    ) -> bytes:
        """Capture a screenshot and return raw bytes.

        Args:
            region: Optional (x, y, width, height) tuple.
            img_format: Image format (jpeg/png).
            quality: JPEG quality (1-100).

        Returns:
            Raw image bytes.
        """
        _ensure_macos_imports()
        try:
            if region:
                x, y, w, h = region
                rect = _Quartz.CGRectMake(x, y, w, h)
            else:
                rect = _Quartz.CGRectInfinite

            image = _Quartz.CGWindowListCreateImage(
                rect,
                _Quartz.kCGWindowListOptionOnScreenOnly,
                _Quartz.kCGNullWindowID,
                _Quartz.kCGWindowImageDefault,
            )

            if image is None:
                raise RuntimeError("CGWindowListCreateImage returned None")

            # Convert CGImage to bytes via PIL
            width = _Quartz.CGImageGetWidth(image)
            height = _Quartz.CGImageGetHeight(image)
            bytes_per_row = _Quartz.CGImageGetBytesPerRow(image)

            data_provider = _Quartz.CGImageGetDataProvider(image)
            raw_data = _Quartz.CGDataProviderCopyData(data_provider)

            from PIL import Image

            pil_image = Image.frombytes(
                "RGBA", (width, height), bytes(raw_data), "raw", "BGRA", bytes_per_row
            )

            if img_format == "jpeg":
                pil_image = pil_image.convert("RGB")

            buf = io.BytesIO()
            pil_image.save(buf, format=img_format.upper(), quality=quality)
            return buf.getvalue()

        except ImportError as e:
            logger.warning("PIL not available for screenshot conversion: %s", e)
            raise
        except Exception as e:
            logger.error("Screenshot capture failed: %s", e)
            raise

    def capture_screenshot_base64(
        self,
        region: tuple[int, int, int, int] | None = None,
        img_format: str = "jpeg",
        quality: int = 85,
    ) -> str:
        """Capture screenshot and return base64-encoded string.

        Args:
            region: Optional (x, y, width, height) tuple.
            img_format: Image format (jpeg/png).
            quality: JPEG quality (1-100).

        Returns:
            Base64-encoded image string.
        """
        raw = self.capture_screenshot(region=region, img_format=img_format, quality=quality)
        return base64.b64encode(raw).decode("utf-8")

    def get_screen_size(self) -> tuple[int, int]:
        """Get the primary screen resolution."""
        if self._screen_size is not None:
            return self._screen_size
        _ensure_macos_imports()
        try:
            main_display = _Quartz.CGMainDisplayID()
            width = _Quartz.CGDisplayPixelsWide(main_display)
            height = _Quartz.CGDisplayPixelsHigh(main_display)
            self._screen_size = (int(width), int(height))
            return self._screen_size
        except Exception:
            try:
                size = _pyautogui.size()
                self._screen_size = (size.width, size.height)
                return self._screen_size
            except Exception:
                return (1920, 1080)

    # ── Tree extraction ──────────────────────────────────────────────────

    def get_active_apps(self, obs: dict[str, Any]) -> list[str]:
        """Return a list of currently running application names."""
        _ensure_macos_imports()
        apps: list[str] = []
        for proc in _psutil.process_iter(["pid", "name"]):
            try:
                apps.append(proc.info["name"] or "")
            except Exception:
                pass
        return apps

    def get_top_app(self, obs: dict[str, Any]) -> str | None:
        """Return the name of the foreground application."""
        try:
            focused = MacUIElement.focused_application()
            if focused:
                return focused.title() or focused.description()
        except Exception as e:
            logger.debug("Failed to get top app: %s", e)
        return None

    def extract_tree(
        self,
        exclude_roles: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract the UI element tree from the focused application.

        Args:
            exclude_roles: Set of AXRole values to exclude from the tree.

        Returns:
            List of UI element dicts with position, size, title, role, etc.
        """
        _ensure_macos_imports()
        if exclude_roles is None:
            exclude_roles = {"Group", "LayoutArea", "LayoutItem", "Unknown"}

        preserved: list[dict[str, Any]] = []

        try:
            focused = MacUIElement.focused_application()
            if focused is None:
                logger.warning("No focused application found")
                return preserved

            self._traverse_elements(focused, preserved, exclude_roles, depth=0, max_depth=50)
        except Exception as e:
            logger.error("Failed to extract UI tree: %s", e)

        return preserved

    def _traverse_elements(
        self,
        element: MacUIElement,
        preserved: list[dict[str, Any]],
        exclude_roles: set[str],
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursively traverse the accessibility tree."""
        if depth > max_depth:
            return

        role = element.role()
        if role not in exclude_roles:
            pos = element.position()
            sz = element.size()
            if pos and sz and pos[0] >= 0 and pos[1] >= 0 and sz[0] > 0 and sz[1] > 0:
                preserved.append({
                    "position": pos,
                    "size": sz,
                    "title": element.title(),
                    "description": element.description(),
                    "value": element.value(),
                    "role": role,
                    "subrole": element.subrole(),
                    "enabled": element.is_enabled(),
                    "depth": depth,
                })

        for child in element.children():
            self._traverse_elements(child, preserved, exclude_roles, depth + 1, max_depth)

    def preserve_nodes(
        self,
        tree: Any,
        exclude_roles: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Traverse the UI tree and return valid, visible nodes."""
        if exclude_roles is None:
            exclude_roles = {"Group", "LayoutArea", "LayoutItem", "Unknown"}

        if isinstance(tree, MacUIElement):
            result: list[dict[str, Any]] = []
            self._traverse_elements(tree, result, exclude_roles, depth=0, max_depth=50)
            return result
        return []

    def linearize_and_annotate_tree(
        self, obs: dict[str, Any], show_all_elements: bool = False
    ) -> str:
        """Build a tab-separated linearized accessibility tree string."""
        _ensure_macos_imports()

        try:
            focused = MacUIElement.focused_application()
            if focused is None:
                self.nodes = []
                return ""
        except Exception:
            self.nodes = []
            return ""

        exclude_roles = {"Group", "LayoutArea", "LayoutItem", "Unknown"}
        if show_all_elements:
            exclude_roles = set()

        preserved = self.preserve_nodes(focused, exclude_roles)

        lines = ["id\trole\ttitle\ttext"]
        for i, node in enumerate(preserved):
            text = node.get("value", "") or node.get("title", "")
            lines.append(f"{i}\t{node['role']}\t{node['title']}\t{text}")

        if self.ocr:
            screenshot = obs.get("screenshot", None)
            if screenshot is not None and hasattr(self, "add_ocr_elements"):
                # Delegate to OCR augmentation if available
                lines, preserved = self.add_ocr_elements(screenshot, lines, preserved)

        self.nodes = preserved
        return "\n".join(lines)

    def find_element(self, element_id: int) -> dict[str, Any]:
        """Look up a UI element by its index in self.nodes."""
        if not self.nodes:
            raise IndexError("No elements in the accessibility tree.")
        try:
            return self.nodes[element_id]
        except IndexError:
            self.index_out_of_range_flag = True
            return self.nodes[0]

    # ── Actions ──────────────────────────────────────────────────────────

    def execute_action(self, action_type: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a desktop automation action.

        Args:
            action_type: Action type (click, type, scroll, hotkey, etc.).
            params: Action-specific parameters.

        Returns:
            Result dict with status and output.
        """
        _ensure_macos_imports()

        action_handlers: dict[str, Any] = {
            "click": self._execute_click,
            "double_click": self._execute_double_click,
            "right_click": self._execute_right_click,
            "type": self._execute_type,
            "key_press": self._execute_key_press,
            "hotkey": self._execute_hotkey,
            "scroll": self._execute_scroll,
            "drag": self._execute_drag,
            "move": self._execute_move,
            "wait": self._execute_wait,
            "screenshot": self._execute_screenshot,
        }

        handler = action_handlers.get(action_type)
        if handler is None:
            return {"status": "error", "message": f"Unknown action type: {action_type}"}

        try:
            result = handler(params)
            return {"status": "completed", "result": result}
        except Exception as e:
            logger.error("Action %s failed: %s", action_type, e)
            return {"status": "failed", "error": str(e)}

    def _execute_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        clicks = int(params.get("clicks", 1))
        button = params.get("button", "left")
        _pyautogui.click(x, y, clicks=clicks, button=button)
        return {"x": x, "y": y, "clicks": clicks, "button": button}

    def _execute_double_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        _pyautogui.doubleClick(x, y)
        return {"x": x, "y": y}

    def _execute_right_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        _pyautogui.rightClick(x, y)
        return {"x": x, "y": y}

    def _execute_type(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params.get("text", ""))
        interval = float(params.get("interval", 0.0))
        _pyautogui.write(text, interval=interval)
        return {"text": text, "length": len(text)}

    def _execute_key_press(self, params: dict[str, Any]) -> dict[str, Any]:
        key = _normalize_key(str(params.get("key", "")))
        _pyautogui.press(key)
        return {"key": key}

    def _execute_hotkey(self, params: dict[str, Any]) -> dict[str, Any]:
        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = keys.split(",")
        keys = [_normalize_key(k.strip()) for k in keys]
        _pyautogui.hotkey(*keys)
        return {"keys": keys}

    def _execute_scroll(self, params: dict[str, Any]) -> dict[str, Any]:
        clicks = int(params.get("clicks", 0))
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            _pyautogui.scroll(clicks, x=int(x), y=int(y))
        else:
            _pyautogui.scroll(clicks)
        return {"clicks": clicks}

    def _execute_drag(self, params: dict[str, Any]) -> dict[str, Any]:
        x1 = int(params.get("x1", 0))
        y1 = int(params.get("y1", 0))
        x2 = int(params.get("x2", 0))
        y2 = int(params.get("y2", 0))
        duration = float(params.get("duration", 0.5))
        _pyautogui.moveTo(x1, y1)
        _pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
        return {"from": (x1, y1), "to": (x2, y2)}

    def _execute_move(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        duration = float(params.get("duration", 0.25))
        _pyautogui.moveTo(x, y, duration=duration)
        return {"x": x, "y": y}

    def _execute_wait(self, params: dict[str, Any]) -> dict[str, Any]:
        import time as _time
        duration = float(params.get("duration", 1.0))
        _time.sleep(duration)
        return {"duration": duration}

    def _execute_screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        region = params.get("region")
        if region and len(region) == 4:
            region = tuple(region)
        else:
            region = None
        quality = int(params.get("quality", 85))
        b64 = self.capture_screenshot_base64(region=region, quality=quality)
        return {"image_base64": b64, "format": "jpeg"}

    # ── Agent actions (for compatibility with ACI base) ──────────────────

    @agent_action
    def open(self, app_or_file_name: str) -> str:
        """Open an application by name."""
        return (
            "import pyautogui; import time; "
            "pyautogui.hotkey('command', 'space', interval=0.5); "
            f"pyautogui.write({app_or_file_name!r}); "
            "pyautogui.press('enter'); time.sleep(1.0)"
        )

    @agent_action
    def switch_applications(self, app_or_file_name: str) -> str:
        """Switch to an application via Cmd+Tab."""
        return (
            "import pyautogui; import time; "
            "pyautogui.hotkey('command', 'tab', interval=0.5); "
            f"pyautogui.write({app_or_file_name!r}); "
            "pyautogui.press('enter'); time.sleep(1.0)"
        )

    @agent_action
    def click(
        self,
        element_id: int,
        num_clicks: int = 1,
        button_type: str = "left",
        hold_keys: list[str] | None = None,
    ) -> str:
        """Click on a UI element by its ID."""
        if hold_keys is None:
            hold_keys = []

        node = self.find_element(element_id)
        x = int(node["position"][0] + node["size"][0] // 2)
        y = int(node["position"][1] + node["size"][1] // 2)

        hold_keys = [_normalize_key(k) for k in hold_keys]
        parts = ["import pyautogui"]
        for k in hold_keys:
            parts.append(f"pyautogui.keyDown({k!r})")
        parts.append(f"pyautogui.click({x}, {y}, clicks={num_clicks}, button={button_type!r})")
        for k in hold_keys:
            parts.append(f"pyautogui.keyUp({k!r})")
        return "; ".join(parts)

    @agent_action
    def type(
        self,
        element_id: int | None = None,
        text: str = "",
        overwrite: bool = False,
        enter: bool = False,
    ) -> str:
        """Type text into an element."""
        try:
            node = self.find_element(element_id) if element_id is not None else None
        except Exception:
            node = None

        parts = ["import pyautogui"]

        if node is not None:
            x = int(node["position"][0] + node["size"][0] // 2)
            y = int(node["position"][1] + node["size"][1] // 2)
            parts.append(f"pyautogui.click({x}, {y})")

        if overwrite:
            parts.append("pyautogui.hotkey('command', 'a', interval=0.5)")
            parts.append("pyautogui.press('backspace')")

        parts.append(f"pyautogui.write({text!r})")

        if enter:
            parts.append("pyautogui.press('enter')")

        return "; ".join(parts)

    @agent_action
    def save_to_knowledge(self, text: list[str]) -> str:
        """Save facts to the persistent scratchpad."""
        self.notes.extend(text)
        return "WAIT"

    @agent_action
    def drag_and_drop(
        self, drag_from_id: int, drop_on_id: int, hold_keys: list[str] | None = None
    ) -> str:
        """Drag one element onto another."""
        if hold_keys is None:
            hold_keys = []

        n1 = self.find_element(drag_from_id)
        n2 = self.find_element(drop_on_id)
        x1 = int(n1["position"][0] + n1["size"][0] // 2)
        y1 = int(n1["position"][1] + n1["size"][1] // 2)
        x2 = int(n2["position"][0] + n2["size"][0] // 2)
        y2 = int(n2["position"][1] + n2["size"][1] // 2)

        parts = ["import pyautogui", f"pyautogui.moveTo({x1}, {y1})"]
        for k in hold_keys:
            parts.append(f"pyautogui.keyDown({k!r})")
        parts.append(f"pyautogui.dragTo({x2}, {y2}, duration=1.0)")
        parts.append("pyautogui.mouseUp()")
        for k in hold_keys:
            parts.append(f"pyautogui.keyUp({k!r})")
        return "; ".join(parts)

    @agent_action
    def scroll(self, element_id: int, clicks: int) -> str:
        """Scroll inside an element."""
        try:
            node = self.find_element(element_id)
        except Exception:
            node = self.find_element(0)

        x = int(node["position"][0] + node["size"][0] // 2)
        y = int(node["position"][1] + node["size"][1] // 2)
        return f"import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.scroll({clicks})"

    @agent_action
    def hotkey(self, keys: list[str]) -> str:
        """Press a hotkey combination."""
        keys = [_normalize_key(k) for k in keys]
        quoted = ", ".join(f"'{k}'" for k in keys)
        return f"import pyautogui; pyautogui.hotkey({quoted}, interval=0.5)"

    @agent_action
    def hold_and_press(
        self, hold_keys: list[str], press_keys: list[str]
    ) -> str:
        """Hold modifier keys while pressing a sequence."""
        hold_keys = [_normalize_key(k) for k in hold_keys]
        press_keys = [_normalize_key(k) for k in press_keys]
        press_str = "[" + ", ".join(f"'{k}'" for k in press_keys) + "]"

        parts = ["import pyautogui"]
        for k in hold_keys:
            parts.append(f"pyautogui.keyDown({k!r})")
        parts.append(f"pyautogui.press({press_str})")
        for k in hold_keys:
            parts.append(f"pyautogui.keyUp({k!r})")
        return "; ".join(parts)

    @agent_action
    def wait(self, time: float) -> str:
        """Wait for a specified duration."""
        return f"import time; time.sleep({time})"

    @agent_action
    def done(self) -> str:
        """Signal successful task completion."""
        return "DONE"

    @agent_action
    def fail(self) -> str:
        """Signal task failure."""
        return "FAIL"