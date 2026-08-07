"""Linux ACI implementation — AT-SPI via pyatspi.

Implements the ACI (Actionable Context Interface) for Linux using the
AT-SPI (Assistive Technology Service Provider Interface) through pyatspi.
Provides UI tree extraction, screenshot capture, and action code generation
for desktop automation.

Note: Platform-specific imports (pyatspi, xdotool) are lazy-loaded
to allow the module to be imported on non-Linux systems for type checking.
"""

from __future__ import annotations

import base64
import io
import logging
import platform
import subprocess
from typing import Any

from skpl_agent.desktop_automation._aci import ACI, agent_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy platform helpers
# ---------------------------------------------------------------------------

_pyautogui: Any = None
_pyatspi: Any = None
_psutil: Any = None
_pil: Any = None


def _ensure_linux_imports() -> None:
    """Lazy-import Linux-specific modules. Raises ImportError on non-Linux."""
    global _pyautogui, _pyatspi, _psutil, _pil
    if _pyatspi is not None:
        return
    if platform.system() != "Linux":
        raise ImportError("LinuxOSACI requires Linux platform")

    import pyautogui as _pyautogui
    import psutil as _psutil

    try:
        import pyatspi as _pyatspi
    except ImportError as e:
        raise ImportError(
            "pyatspi not installed. Install with: pip install pyatspi"
        ) from e

    try:
        import PIL as _pil
    except ImportError:
        pass


def _normalize_key(key: str) -> str:
    """Convert key names for pyautogui compatibility on Linux."""
    key_map: dict[str, str] = {
        "super": "win",
        "meta": "win",
        "win": "win",
        "command": "win",
        "cmd": "win",
        "option": "alt",
        "alt": "alt",
        "altgr": "alt",
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
# xdotool helpers
# ---------------------------------------------------------------------------

def _run_xdotool(args: list[str]) -> str:
    """Run an xdotool command and return stdout.

    Args:
        args: List of xdotool arguments.

    Returns:
        Command stdout, or empty string on failure.
    """
    try:
        result = subprocess.run(
            ["xdotool"] + args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("xdotool failed: %s", result.stderr.strip())
            return ""
        return result.stdout.strip()
    except FileNotFoundError:
        logger.warning("xdotool not found. Install with: sudo apt install xdotool")
        return ""
    except subprocess.TimeoutExpired:
        logger.warning("xdotool timed out")
        return ""
    except Exception as e:
        logger.warning("xdotool error: %s", e)
        return ""


def _get_active_window_id() -> str:
    """Get the X11 window ID of the currently active window."""
    return _run_xdotool(["getactivewindow"])


def _get_window_name(window_id: str) -> str:
    """Get the name/title of an X11 window."""
    return _run_xdotool(["getwindowname", window_id])


def _focus_window(window_id: str) -> bool:
    """Focus an X11 window by ID."""
    result = _run_xdotool(["windowfocus", window_id])
    return bool(result) or True  # xdotool windowfocus has no output on success


def _get_window_geometry(window_id: str) -> tuple[int, int, int, int] | None:
    """Get window geometry as (x, y, width, height)."""
    output = _run_xdotool(["getwindowgeometry", "--shell", window_id])
    if not output:
        return None
    x = y = w = h = 0
    for line in output.split("\n"):
        if line.startswith("X="):
            x = int(line.split("=")[1])
        elif line.startswith("Y="):
            y = int(line.split("=")[1])
        elif line.startswith("WIDTH="):
            w = int(line.split("=")[1])
        elif line.startswith("HEIGHT="):
            h = int(line.split("=")[1])
    return (x, y, w, h)


# ---------------------------------------------------------------------------
# LinuxUIElement
# ---------------------------------------------------------------------------

class LinuxUIElement:
    """Wrapper around a pyatspi accessible object.

    Provides safe attribute access and tree traversal for AT-SPI
    accessible objects on Linux.
    """

    # Role mapping from AT-SPI to human-readable names
    ROLE_MAP: dict[str, str] = {
        "push button": "Button",
        "toggle button": "ToggleButton",
        "menu item": "MenuItem",
        "check box": "CheckBox",
        "radio button": "RadioButton",
        "text": "Text",
        "label": "Label",
        "panel": "Panel",
        "window": "Window",
        "menu": "Menu",
        "combo box": "ComboBox",
        "list": "List",
        "list item": "ListItem",
        "table": "Table",
        "table cell": "TableCell",
        "scroll bar": "ScrollBar",
        "slider": "Slider",
        "spin button": "SpinButton",
        "tool bar": "ToolBar",
        "status bar": "StatusBar",
        "tree": "Tree",
        "tree item": "TreeItem",
        "page tab": "Tab",
        "page tab list": "TabList",
        "link": "Link",
        "image": "Image",
        "icon": "Icon",
        "separator": "Separator",
        "dialog": "Dialog",
        "frame": "Frame",
        "tool tip": "ToolTip",
        "progress bar": "ProgressBar",
        "split pane": "SplitPane",
        "paragraph": "Paragraph",
        "heading": "Heading",
        "section": "Section",
    }

    def __init__(self, element: Any = None) -> None:
        _ensure_linux_imports()
        self._element = element

    def _safe_get(self, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from the AT-SPI element."""
        try:
            return getattr(self._element, attr, default)
        except Exception:
            return default

    def role(self) -> str:
        """Return the human-readable role name."""
        try:
            role_name = self._element.getRoleName()
            return self.ROLE_MAP.get(role_name.lower(), role_name)
        except Exception:
            return "Unknown"

    def role_name(self) -> str:
        """Return the raw AT-SPI role name."""
        try:
            return self._element.getRoleName()
        except Exception:
            return "unknown"

    def name(self) -> str:
        """Return the accessible name."""
        return str(self._safe_get("name", ""))

    def description(self) -> str:
        """Return the accessible description."""
        return str(self._safe_get("description", ""))

    def position(self) -> tuple[int, int] | None:
        """Return the (x, y) position of this element."""
        try:
            extents = self._element.queryComponent().getExtents(_pyatspi.DESKTOP_COORDS)
            return (extents.x, extents.y)
        except Exception:
            return None

    def size(self) -> tuple[int, int] | None:
        """Return the (width, height) of this element."""
        try:
            extents = self._element.queryComponent().getExtents(_pyatspi.DESKTOP_COORDS)
            return (extents.width, extents.height)
        except Exception:
            return None

    def bounding_box(self) -> tuple[int, int, int, int] | None:
        """Return the (x, y, width, height) bounding box."""
        pos = self.position()
        sz = self.size()
        if pos and sz:
            return (pos[0], pos[1], sz[0], sz[1])
        return None

    def children(self) -> list[LinuxUIElement]:
        """Return child elements."""
        try:
            child_count = self._element.childCount
            result: list[LinuxUIElement] = []
            for i in range(child_count):
                child = self._element.getChildAtIndex(i)
                if child:
                    result.append(LinuxUIElement(child))
            return result
        except Exception:
            return []

    def parent(self) -> LinuxUIElement | None:
        """Return the parent element."""
        try:
            p = self._element.parent
            if p:
                return LinuxUIElement(p)
        except Exception:
            pass
        return None

    def state_set(self) -> set[str]:
        """Return the set of active states for this element."""
        try:
            return set(self._element.getState().getStates())
        except Exception:
            return set()

    def is_enabled(self) -> bool:
        """Check if the element is enabled."""
        return "enabled" in self.state_set()

    def is_focused(self) -> bool:
        """Check if the element is focused."""
        return "focused" in self.state_set()

    def is_visible(self) -> bool:
        """Check if the element is visible."""
        return "visible" in self.state_set() and "showing" in self.state_set()

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
            and self.is_visible()
        )

    def text(self) -> str:
        """Return the text content of the element."""
        try:
            text_iface = self._element.queryText()
            return text_iface.getText(0, text_iface.characterCount)
        except Exception:
            pass
        return self.name() or self.description()

    def parse(self) -> dict[str, Any]:
        """Return a dict representation of this element."""
        pos = self.position()
        sz = self.size()
        return {
            "position": pos,
            "size": sz,
            "name": self.name(),
            "description": self.description(),
            "text": self.text(),
            "role": self.role(),
            "role_name": self.role_name(),
            "enabled": self.is_enabled(),
            "visible": self.is_visible(),
            "focused": self.is_focused(),
        }

    @staticmethod
    def get_desktop() -> LinuxUIElement:
        """Return the desktop root accessible."""
        _ensure_linux_imports()
        registry = _pyatspi.Registry()
        desktop = registry.getDesktop(0)
        return LinuxUIElement(desktop)

    @staticmethod
    def get_active_window() -> LinuxUIElement | None:
        """Return the accessible for the currently active window."""
        _ensure_linux_imports()
        try:
            desktop = LinuxUIElement.get_desktop()
            for child in desktop.children():
                if child.is_focused() or child.role_name() == "frame":
                    if child.is_visible():
                        return child
        except Exception as e:
            logger.debug("Failed to get active window: %s", e)
        return None

    @staticmethod
    def get_running_applications() -> list[dict[str, Any]]:
        """Return a list of running applications."""
        _ensure_linux_imports()
        apps: list[dict[str, Any]] = []
        try:
            desktop = LinuxUIElement.get_desktop()
            for child in desktop.children():
                if child.role_name() in ("application", "frame"):
                    apps.append({
                        "name": child.name(),
                        "description": child.description(),
                        "role": child.role(),
                    })
        except Exception as e:
            logger.warning("Failed to list applications: %s", e)
        return apps

    def __repr__(self) -> str:
        return f"LinuxUIElement(role={self.role()!r}, name={self.name()!r})"


# ---------------------------------------------------------------------------
# LinuxOSACI
# ---------------------------------------------------------------------------

class LinuxOSACI(ACI):
    """Linux desktop automation via AT-SPI + pyautogui + xdotool.

    Extracts the UI element tree from the active window via AT-SPI,
    and generates pyautogui code strings for each action. Uses xdotool
    for window management operations.

    Usage:
        >>> aci = LinuxOSACI(top_app_only=True, ocr=False)
        >>> obs = {"screenshot": b"..."}
        >>> tree_text = aci.linearize_and_annotate_tree(obs)
        >>> code = aci.click(element_id=3)
        >>> exec(code)
    """

    def __init__(self, top_app_only: bool = True, ocr: bool = False) -> None:
        super().__init__(top_app_only=top_app_only, ocr=ocr)
        _ensure_linux_imports()
        self._screen_size: tuple[int, int] | None = None
        self._active_window_id: str = ""

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
        _ensure_linux_imports()
        try:
            from PIL import Image

            if region:
                x, y, w, h = region
                img = _pyautogui.screenshot(region=(x, y, w, h))
            else:
                img = _pyautogui.screenshot()

            if img_format == "jpeg" and img.mode == "RGBA":
                img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format=img_format.upper(), quality=quality)
            return buf.getvalue()

        except ImportError as e:
            logger.warning("PIL not available: %s", e)
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
        """Capture screenshot and return base64-encoded string."""
        raw = self.capture_screenshot(region=region, img_format=img_format, quality=quality)
        return base64.b64encode(raw).decode("utf-8")

    def get_screen_size(self) -> tuple[int, int]:
        """Get the primary screen resolution."""
        if self._screen_size is not None:
            return self._screen_size
        try:
            size = _pyautogui.size()
            self._screen_size = (size.width, size.height)
            return self._screen_size
        except Exception:
            return (1920, 1080)

    # ── Window management (xdotool) ──────────────────────────────────────

    def get_active_window_id(self) -> str:
        """Get the X11 window ID of the currently active window."""
        self._active_window_id = _get_active_window_id()
        return self._active_window_id

    def get_active_window_name(self) -> str:
        """Get the name of the currently active window."""
        wid = self.get_active_window_id()
        if wid:
            return _get_window_name(wid)
        return ""

    def focus_window(self, window_id: str) -> bool:
        """Focus a window by its X11 ID."""
        return _focus_window(window_id)

    def get_window_geometry(
        self, window_id: str
    ) -> tuple[int, int, int, int] | None:
        """Get (x, y, width, height) of a window."""
        return _get_window_geometry(window_id)

    def move_window(self, window_id: str, x: int, y: int) -> bool:
        """Move a window to specified coordinates."""
        _run_xdotool(["windowmove", window_id, str(x), str(y)])
        return True

    def resize_window(self, window_id: str, w: int, h: int) -> bool:
        """Resize a window."""
        _run_xdotool(["windowsize", window_id, str(w), str(h)])
        return True

    # ── Tree extraction ──────────────────────────────────────────────────

    def get_active_apps(self, obs: dict[str, Any]) -> list[str]:
        """Return a list of currently running application names."""
        _ensure_linux_imports()
        apps: list[str] = []
        for proc in _psutil.process_iter(["pid", "name"]):
            try:
                apps.append(proc.info["name"] or "")
            except Exception:
                pass
        return apps

    def get_top_app(self, obs: dict[str, Any]) -> str | None:
        """Return the name of the foreground application."""
        return self.get_active_window_name() or None

    def extract_tree(
        self,
        exclude_roles: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract the UI element tree from the active window.

        Args:
            exclude_roles: Set of AT-SPI role names to exclude.

        Returns:
            List of UI element dicts.
        """
        _ensure_linux_imports()
        if exclude_roles is None:
            exclude_roles = {"filler", "separator", "unknown", "panel"}

        preserved: list[dict[str, Any]] = []

        try:
            active = LinuxUIElement.get_active_window()
            if active is None:
                logger.warning("No active window found via AT-SPI")
                return preserved

            self._traverse_elements(active, preserved, exclude_roles, depth=0, max_depth=50)
        except Exception as e:
            logger.error("Failed to extract UI tree: %s", e)

        return preserved

    def _traverse_elements(
        self,
        element: LinuxUIElement,
        preserved: list[dict[str, Any]],
        exclude_roles: set[str],
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursively traverse the AT-SPI tree."""
        if depth > max_depth:
            return

        role_name = element.role_name()
        if role_name not in exclude_roles:
            if element.is_valid():
                pos = element.position()
                sz = element.size()
                preserved.append({
                    "position": pos,
                    "size": sz,
                    "name": element.name(),
                    "description": element.description(),
                    "text": element.text(),
                    "role": element.role(),
                    "role_name": role_name,
                    "enabled": element.is_enabled(),
                    "focused": element.is_focused(),
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
            exclude_roles = {"filler", "separator", "unknown", "panel"}

        if isinstance(tree, LinuxUIElement):
            result: list[dict[str, Any]] = []
            self._traverse_elements(tree, result, exclude_roles, depth=0, max_depth=50)
            return result
        return []

    def linearize_and_annotate_tree(
        self, obs: dict[str, Any], show_all_elements: bool = False
    ) -> str:
        """Build a tab-separated linearized accessibility tree string."""
        _ensure_linux_imports()

        try:
            active = LinuxUIElement.get_active_window()
            if active is None:
                self.nodes = []
                return ""
        except Exception:
            self.nodes = []
            return ""

        exclude_roles = {"filler", "separator", "unknown", "panel"}
        if show_all_elements:
            exclude_roles = set()

        preserved = self.preserve_nodes(active, exclude_roles)

        lines = ["id\trole\tname\ttext"]
        for i, node in enumerate(preserved):
            text = node.get("text", "") or node.get("name", "")
            lines.append(f"{i}\t{node['role']}\t{node['name']}\t{text}")

        if self.ocr:
            screenshot = obs.get("screenshot", None)
            if screenshot is not None and hasattr(self, "add_ocr_elements"):
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
        _ensure_linux_imports()

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
            "focus_window": self._execute_focus_window,
            "move_window": self._execute_move_window,
            "resize_window": self._execute_resize_window,
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

    def _execute_focus_window(self, params: dict[str, Any]) -> dict[str, Any]:
        window_id = str(params.get("window_id", ""))
        success = self.focus_window(window_id)
        return {"window_id": window_id, "success": success}

    def _execute_move_window(self, params: dict[str, Any]) -> dict[str, Any]:
        window_id = str(params.get("window_id", ""))
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        self.move_window(window_id, x, y)
        return {"window_id": window_id, "x": x, "y": y}

    def _execute_resize_window(self, params: dict[str, Any]) -> dict[str, Any]:
        window_id = str(params.get("window_id", ""))
        w = int(params.get("width", 800))
        h = int(params.get("height", 600))
        self.resize_window(window_id, w, h)
        return {"window_id": window_id, "width": w, "height": h}

    # ── Agent actions (for compatibility with ACI base) ──────────────────

    @agent_action
    def open(self, app_or_file_name: str) -> str:
        """Open an application via xdg-open or Alt+F2."""
        return (
            "import pyautogui; import time; "
            "pyautogui.hotkey('alt', 'f2', interval=0.5); "
            f"pyautogui.write({app_or_file_name!r}); "
            "pyautogui.press('enter'); time.sleep(1.0)"
        )

    @agent_action
    def switch_applications(self, app_or_file_name: str) -> str:
        """Switch to an application via Alt+Tab."""
        return (
            "import pyautogui; import time; "
            "pyautogui.hotkey('alt', 'tab', interval=0.5); "
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
            parts.append("pyautogui.hotkey('ctrl', 'a', interval=0.5)")
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