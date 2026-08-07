"""Windows ACI implementation — pywinauto + UIA backend.

Adapted from Agent-S gui_agents/s1/aci/WindowsOSACI.py.
Extracts UI elements via Windows UI Automation (UIA) and generates
pyautogui action code strings.

Note: Platform-specific imports (pywinauto, win32gui, etc.) are lazy-loaded
to allow the module to be imported on non-Windows systems for type checking.
"""

from __future__ import annotations

import base64
import logging
import os
import platform
from typing import Any

import numpy as np
import psutil
import requests

from skpl_agent.desktop_automation._aci import ACI, agent_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy platform helpers
# ---------------------------------------------------------------------------

_pywinauto = None
_win32gui = None
_win32process = None


def _ensure_windows_imports() -> None:
    """Lazy-import Windows-specific modules. Raises ImportError on non-Windows."""
    global _pywinauto, _win32gui, _win32process
    if _pywinauto is not None:
        return
    if platform.system() != "Windows":
        raise ImportError("WindowsACI requires Windows platform")
    import pywinauto as _pywinauto
    import win32gui as _win32gui
    import win32process as _win32process


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_key(key: str) -> str:
    """Convert 'ctrl' to 'control' for pyautogui compatibility."""
    return "ctrl" if key == "control" else key


def _list_apps_in_directories() -> list[str]:
    """Scan Program Files directories for installed .exe names."""
    directories = [
        os.environ.get("PROGRAMFILES", "C:\\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
    ]
    apps: list[str] = []
    for directory in directories:
        if os.path.exists(directory):
            for root, _dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith(".exe"):
                        apps.append(file)
    return apps


def _box_iou(boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
    """Compute pairwise IoU between two sets of [x1, y1, x2, y2] boxes.

    This is a local copy to avoid the cross-package import from Agent-S.
    """
    N, M = len(boxes1), len(boxes2)
    if N == 0 or M == 0:
        return np.zeros((N, M), dtype=np.float32)

    x1 = np.maximum(boxes1[:, None, 0], boxes2[None, :, 0])
    y1 = np.maximum(boxes1[:, None, 1], boxes2[None, :, 1])
    x2 = np.minimum(boxes1[:, None, 2], boxes2[None, :, 2])
    y2 = np.minimum(boxes1[:, None, 3], boxes2[None, :, 3])

    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)

    area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
    area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])
    union = area1[:, None] + area2[None, :] - inter

    return np.where(union > 0, inter / union, 0)


# ---------------------------------------------------------------------------
# UIElement
# ---------------------------------------------------------------------------

class UIElement:
    """Wrapper around a pywinauto control for safe attribute access."""

    def __init__(self, element: Any = None) -> None:
        _ensure_windows_imports()
        if isinstance(element, _pywinauto.application.WindowSpecification):
            self.element = element.wrapper_object()
        else:
            self.element = element

    def get_attribute_names(self) -> list[str]:
        return list(self.element.element_info.get_properties().keys())

    def attribute(self, key: str) -> Any:
        return self.element.element_info.get_properties().get(key, None)

    def children(self) -> list[UIElement]:
        try:
            return [UIElement(child) for child in self.element.children()]
        except Exception:
            return []

    def role(self) -> str:
        return self.element.element_info.control_type

    def position(self) -> tuple[int, int] | None:
        rect = self.element.rectangle()
        return (rect.left, rect.top)

    def size(self) -> tuple[int, int] | None:
        rect = self.element.rectangle()
        return (rect.width(), rect.height())

    def title(self) -> str:
        return self.element.element_info.name

    def text(self) -> str:
        return self.element.window_text()

    def is_valid(self) -> bool:
        return self.position() is not None and self.size() is not None

    def parse(self) -> dict[str, Any]:
        return {
            "position": self.position(),
            "size": self.size(),
            "title": self.title(),
            "text": self.text(),
            "role": self.role(),
        }

    @staticmethod
    def get_current_applications(obs: dict[str, Any]) -> list[str]:
        apps: list[str] = []
        for proc in psutil.process_iter(["pid", "name"]):
            apps.append(proc.info["name"])
        return apps

    @staticmethod
    def get_top_app(obs: dict[str, Any]) -> str | None:
        _ensure_windows_imports()
        hwnd = _win32gui.GetForegroundWindow()
        _, pid = _win32process.GetWindowThreadProcessId(hwnd)
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["pid"] == pid:
                return proc.info["name"]
        return None

    @staticmethod
    def list_apps_in_directories() -> list[str]:
        return _list_apps_in_directories()

    @staticmethod
    def system_wide_element() -> UIElement:
        _ensure_windows_imports()
        desktop = _pywinauto.Desktop(backend="uia")
        return UIElement(desktop)

    def __repr__(self) -> str:
        return f"UIElement({self.element})"


# ---------------------------------------------------------------------------
# WindowsACI
# ---------------------------------------------------------------------------

class WindowsACI(ACI):
    """Windows desktop automation via UIA + pywinauto.

    Extracts the UI element tree from the foreground window, optionally
    augments it with OCR, and generates pyautogui code strings for each
    action (click, type, scroll, hotkey, etc.).

    Usage:
        >>> aci = WindowsACI(top_app_only=True, ocr=False)
        >>> obs = {"screenshot": b"..."}
        >>> tree_text = aci.linearize_and_annotate_tree(obs)
        >>> code = aci.click(element_id=3)
        >>> exec(code)  # or send to the edge node for execution
    """

    def __init__(self, top_app_only: bool = True, ocr: bool = False) -> None:
        super().__init__(top_app_only=top_app_only, ocr=ocr)
        self.all_apps = _list_apps_in_directories()

    # ── Tree extraction ──────────────────────────────────────────────────

    def get_active_apps(self, obs: dict[str, Any]) -> list[str]:
        return UIElement.get_current_applications(obs)

    def get_top_app(self, obs: dict[str, Any]) -> str | None:
        return UIElement.get_top_app(obs)

    def preserve_nodes(
        self, tree: Any, exclude_roles: set[str] | None = None
    ) -> list[dict[str, Any]]:
        if exclude_roles is None:
            exclude_roles = set()

        preserved: list[dict[str, Any]] = []

        def traverse(element: UIElement) -> None:
            role = element.role()
            if role not in exclude_roles:
                position = element.position()
                size = element.size()
                if position and size:
                    x, y = position
                    w, h = size
                    if x >= 0 and y >= 0 and w > 0 and h > 0:
                        preserved.append({
                            "position": (x, y),
                            "size": (w, h),
                            "title": element.title(),
                            "text": element.text(),
                            "role": role,
                        })
            for child in element.children():
                traverse(child)

        traverse(tree)
        return preserved

    def _extract_elements_from_screenshot(
        self, screenshot: bytes
    ) -> dict[str, Any]:
        url = os.environ.get("OCR_SERVER_ADDRESS")
        if not url:
            raise EnvironmentError("OCR_SERVER_ADDRESS environment variable not set")

        encoded = base64.b64encode(screenshot).decode("utf-8")
        response = requests.post(url, json={"img_bytes": encoded})

        if response.status_code != 200:
            return {"error": f"Request failed with status {response.status_code}", "results": []}
        return response.json()

    def add_ocr_elements(
        self,
        screenshot: bytes | None,
        linearized_tree: list[str],
        preserved_nodes: list[dict[str, Any]],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Augment the accessibility tree with OCR-detected text elements."""
        if screenshot is None:
            return linearized_tree, preserved_nodes

        if preserved_nodes:
            tree_bboxes = np.array(
                [
                    [n["position"][0], n["position"][1],
                     n["position"][0] + n["size"][0],
                     n["position"][1] + n["size"][1]]
                    for n in preserved_nodes
                ],
                dtype=np.float32,
            )
        else:
            tree_bboxes = np.empty((0, 4), dtype=np.float32)

        try:
            ocr_result = self._extract_elements_from_screenshot(screenshot)
        except Exception:
            return linearized_tree, preserved_nodes

        if not ocr_result or not ocr_result.get("results"):
            return linearized_tree, preserved_nodes

        idx = len(preserved_nodes)
        ocr_boxes = np.array(
            [
                [
                    int(box.get("left", 0)), int(box.get("top", 0)),
                    int(box.get("right", 0)), int(box.get("bottom", 0)),
                ]
                for _, _, box in ocr_result["results"]
            ],
            dtype=np.float32,
        )

        max_ious = (
            _box_iou(tree_bboxes, ocr_boxes).max(axis=0)
            if len(tree_bboxes) > 0
            else np.zeros(len(ocr_boxes))
        )

        for i, ((_, content, box), max_iou) in enumerate(
            zip(ocr_result["results"], max_ious)
        ):
            if max_iou < 0.1:
                x1, y1 = int(box.get("left", 0)), int(box.get("top", 0))
                x2, y2 = int(box.get("right", 0)), int(box.get("bottom", 0))
                linearized_tree.append(f"{idx}\tButton\t\t{content}\t\t")
                preserved_nodes.append({
                    "position": (x1, y1),
                    "size": (x2 - x1, y2 - y1),
                    "title": "",
                    "text": content,
                    "role": "Button",
                })
                idx += 1

        return linearized_tree, preserved_nodes

    def linearize_and_annotate_tree(
        self, obs: dict[str, Any], show_all_elements: bool = False
    ) -> str:
        _ensure_windows_imports()
        desktop = _pywinauto.Desktop(backend="uia")
        try:
            tree = desktop.window(
                handle=_win32gui.GetForegroundWindow()
            ).wrapper_object()
        except Exception:
            self.nodes = []
            return ""

        exclude_roles = {"Pane", "Group", "Unknown"}
        preserved = self.preserve_nodes(UIElement(tree), exclude_roles)

        if not preserved and show_all_elements:
            preserved = self.preserve_nodes(UIElement(tree), set())

        lines = ["id\trole\ttitle\ttext"]
        for i, node in enumerate(preserved):
            lines.append(f"{i}\t{node['role']}\t{node['title']}\t{node['text']}")

        if self.ocr:
            screenshot = obs.get("screenshot", None)
            if screenshot is not None:
                lines, preserved = self.add_ocr_elements(screenshot, lines, preserved)

        self.nodes = preserved
        return "\n".join(lines)

    def find_element(self, element_id: int) -> dict[str, Any]:
        if not self.nodes:
            raise IndexError("No elements in the accessibility tree.")
        try:
            return self.nodes[element_id]
        except IndexError:
            self.index_out_of_range_flag = True
            return self.nodes[0]

    # ── Actions ──────────────────────────────────────────────────────────

    @agent_action
    def open(self, app_or_file_name: str) -> str:
        """Open an application or file via Win+R.

        Args:
            app_or_file_name: Name of the application or file to open.
        """
        return (
            "import pyautogui; import time; "
            f"pyautogui.hotkey('win', 'r', interval=0.5); "
            f"pyautogui.typewrite({app_or_file_name!r}); "
            "pyautogui.press('enter'); time.sleep(1.0)"
        )

    @agent_action
    def switch_applications(self, app_or_file_name: str) -> str:
        """Switch to a different application via Win+D + search.

        Args:
            app_or_file_name: Name of the application to switch to.
        """
        return (
            "import pyautogui; import time; "
            "pyautogui.hotkey('win', 'd', interval=0.5); "
            f"pyautogui.typewrite({app_or_file_name!r}); "
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
        """Click on a UI element by its ID.

        Args:
            element_id: ID of the element to click.
            num_clicks: Number of clicks (default 1).
            button_type: Mouse button — 'left', 'middle', or 'right'.
            hold_keys: Keys to hold while clicking.
        """
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
        """Type text into an element (or at the current cursor).

        Args:
            element_id: ID of the target element. If None, types at cursor.
            text: Text to type.
            overwrite: If True, clear existing text first (Ctrl+A, Backspace).
            enter: If True, press Enter after typing.
        """
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
        """Save facts or text to the persistent scratchpad.

        Args:
            text: Strings to save to the knowledge notes.
        """
        self.notes.extend(text)
        return "WAIT"

    @agent_action
    def drag_and_drop(
        self, drag_from_id: int, drop_on_id: int, hold_keys: list[str] | None = None
    ) -> str:
        """Drag one element onto another.

        Args:
            drag_from_id: ID of the element to drag.
            drop_on_id: ID of the element to drop onto.
            hold_keys: Keys to hold while dragging.
        """
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
        """Scroll inside an element.

        Args:
            element_id: ID of the element to scroll in.
            clicks: Positive = up, negative = down.
        """
        try:
            node = self.find_element(element_id)
        except Exception:
            node = self.find_element(0)

        x = int(node["position"][0] + node["size"][0] // 2)
        y = int(node["position"][1] + node["size"][1] // 2)
        return f"import pyautogui; pyautogui.moveTo({x}, {y}); pyautogui.scroll({clicks})"

    @agent_action
    def hotkey(self, keys: list[str]) -> str:
        """Press a hotkey combination.

        Args:
            keys: Keys to press together, e.g. ['ctrl', 'c'].
        """
        keys = [_normalize_key(k) for k in keys]
        quoted = ", ".join(f"'{k}'" for k in keys)
        return f"import pyautogui; pyautogui.hotkey({quoted}, interval=0.5)"

    @agent_action
    def hold_and_press(
        self, hold_keys: list[str], press_keys: list[str]
    ) -> str:
        """Hold modifier keys while pressing a sequence.

        Args:
            hold_keys: Keys to hold down.
            press_keys: Keys to press in sequence.
        """
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
        """Wait for a specified duration.

        Args:
            time: Duration in seconds.
        """
        return f"import time; time.sleep({time})"

    @agent_action
    def done(self) -> str:
        """Signal successful task completion."""
        return "DONE"

    @agent_action
    def fail(self) -> str:
        """Signal task failure."""
        return "FAIL"