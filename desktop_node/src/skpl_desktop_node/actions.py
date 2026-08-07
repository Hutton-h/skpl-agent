"""动作执行器 — 鼠标、键盘、截图、OCR 等桌面操作的具体实现."""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# 延迟导入 — 这些包在安装脚本中才安装
_IMPORT_ERRORS: dict[str, str] = {}


def _get_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        return pyautogui
    except ImportError as e:
        _IMPORT_ERRORS["pyautogui"] = str(e)
        return None


def _get_pillow():
    try:
        from PIL import Image
        return Image
    except ImportError as e:
        _IMPORT_ERRORS["PIL"] = str(e)
        return None


def _get_mss():
    try:
        import mss
        return mss
    except ImportError as e:
        _IMPORT_ERRORS["mss"] = str(e)
        return None


def _get_keyboard():
    try:
        import keyboard
        return keyboard
    except ImportError as e:
        _IMPORT_ERRORS["keyboard"] = str(e)
        return None


# ── 动作执行 ──────────────────────────────────────────────────────────


def _make_result(
    success: bool,
    action_id: str = "",
    action_type: str = "",
    data: dict[str, Any] | None = None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "action_type": action_type,
        "success": success,
        "data": data or {},
        "error": error,
        "timestamp": time.time(),
    }


def execute_click(
    x: int, y: int, button: str = "left", clicks: int = 1,
) -> dict[str, Any]:
    """执行鼠标点击。"""
    try:
        pg = _get_pyautogui()
        if pg is None:
            return _make_result(False, error="pyautogui 未安装")
        pg.click(x, y, button=button, clicks=clicks)
        return _make_result(True, data={"x": x, "y": y, "button": button})
    except Exception as e:
        logger.error("click 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_double_click(x: int, y: int) -> dict[str, Any]:
    """执行鼠标双击。"""
    return execute_click(x, y, clicks=2)


def execute_right_click(x: int, y: int) -> dict[str, Any]:
    """执行鼠标右键点击。"""
    return execute_click(x, y, button="right")


def execute_type(text: str, interval: float = 0.05) -> dict[str, Any]:
    """输入文本。"""
    try:
        pg = _get_pyautogui()
        if pg is None:
            return _make_result(False, error="pyautogui 未安装")
        pg.typewrite(text, interval=interval)
        return _make_result(True, data={"text": text})
    except Exception as e:
        logger.error("type 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_scroll(clicks: int, x: int | None = None, y: int | None = None) -> dict[str, Any]:
    """执行滚动。"""
    try:
        pg = _get_pyautogui()
        if pg is None:
            return _make_result(False, error="pyautogui 未安装")
        pg.scroll(clicks, x=x, y=y)
        return _make_result(True, data={"clicks": clicks, "x": x, "y": y})
    except Exception as e:
        logger.error("scroll 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_hotkey(keys: list[str]) -> dict[str, Any]:
    """执行快捷键组合。"""
    try:
        kb = _get_keyboard()
        if kb is None:
            # 回退到 pyautogui
            pg = _get_pyautogui()
            if pg is None:
                return _make_result(False, error="keyboard 和 pyautogui 均未安装")
            pg.hotkey(*keys)
        else:
            kb.press_and_release("+".join(keys))
        return _make_result(True, data={"keys": keys})
    except Exception as e:
        logger.error("hotkey 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_key_press(key: str) -> dict[str, Any]:
    """按下并释放单个按键。"""
    try:
        pg = _get_pyautogui()
        if pg is None:
            return _make_result(False, error="pyautogui 未安装")
        pg.press(key)
        return _make_result(True, data={"key": key})
    except Exception as e:
        logger.error("key_press 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_move(x: int, y: int, duration: float = 0.5) -> dict[str, Any]:
    """移动鼠标到指定位置。"""
    try:
        pg = _get_pyautogui()
        if pg is None:
            return _make_result(False, error="pyautogui 未安装")
        pg.moveTo(x, y, duration=duration)
        return _make_result(True, data={"x": x, "y": y})
    except Exception as e:
        logger.error("move 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_drag(
    start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0,
) -> dict[str, Any]:
    """拖拽操作。"""
    try:
        pg = _get_pyautogui()
        if pg is None:
            return _make_result(False, error="pyautogui 未安装")
        pg.moveTo(start_x, start_y)
        pg.drag(end_x - start_x, end_y - start_y, duration=duration)
        return _make_result(True, data={
            "start": [start_x, start_y], "end": [end_x, end_y],
        })
    except Exception as e:
        logger.error("drag 失败: %s", e)
        return _make_result(False, error=str(e))


def execute_screenshot(quality: int = 85) -> dict[str, Any]:
    """截取整个屏幕，返回 base64 编码的 PNG。"""
    try:
        mss = _get_mss()
        if mss is not None:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # 主显示器
                img = sct.grab(monitor)
                pil_img = _mss_to_pil(img)
        else:
            pg = _get_pyautogui()
            if pg is None:
                return _make_result(False, error="截图库未安装（需要 mss 或 pyautogui）")
            pil_img = pg.screenshot()

        # 转换为 base64
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        img_base64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return _make_result(True, data={
            "image_base64": img_base64,
            "format": "png",
            "width": pil_img.width,
            "height": pil_img.height,
        })
    except Exception as e:
        logger.error("screenshot 失败: %s", e)
        return _make_result(False, error=str(e))


def _mss_to_pil(img):
    """将 mss 截图转换为 PIL Image。"""
    Image = _get_pillow()
    if Image is None:
        raise ImportError("PIL 未安装")
    return Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")


def execute_wait(seconds: float) -> dict[str, Any]:
    """等待指定秒数。"""
    time.sleep(seconds)
    return _make_result(True, data={"waited": seconds})


def get_system_info() -> dict[str, Any]:
    """获取系统信息。"""
    import platform
    import psutil

    screen_width, screen_height = 0, 0
    try:
        pg = _get_pyautogui()
        if pg:
            screen_width, screen_height = pg.size()
    except Exception:
        pass

    return {
        "os_name": platform.system(),
        "os_version": platform.version(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "total_memory_mb": psutil.virtual_memory().total // (1024 * 1024),
        "screen_width": screen_width,
        "screen_height": screen_height,
    }


# ── 动作分发映射 ──────────────────────────────────────────────────────

ACTION_HANDLERS: dict[str, callable] = {
    "click": lambda p: execute_click(
        p.get("x", 0), p.get("y", 0),
        p.get("button", "left"), p.get("clicks", 1),
    ),
    "double_click": lambda p: execute_double_click(
        p.get("x", 0), p.get("y", 0),
    ),
    "right_click": lambda p: execute_right_click(
        p.get("x", 0), p.get("y", 0),
    ),
    "type": lambda p: execute_type(
        p.get("text", ""), p.get("interval", 0.05),
    ),
    "scroll": lambda p: execute_scroll(
        p.get("clicks", 0), p.get("x"), p.get("y"),
    ),
    "hotkey": lambda p: execute_hotkey(p.get("keys", [])),
    "key_press": lambda p: execute_key_press(p.get("key", "")),
    "move": lambda p: execute_move(
        p.get("x", 0), p.get("y", 0),
        p.get("duration", 0.5),
    ),
    "drag": lambda p: execute_drag(
        p.get("start_x", 0), p.get("start_y", 0),
        p.get("end_x", 0), p.get("end_y", 0),
        p.get("duration", 1.0),
    ),
    "screenshot": lambda p: execute_screenshot(
        p.get("quality", 85),
    ),
    "wait": lambda p: execute_wait(p.get("seconds", 1.0)),
    "get_screen_size": lambda p: _get_screen_size(),
}


def _get_screen_size() -> dict[str, Any]:
    try:
        pg = _get_pyautogui()
        if pg:
            w, h = pg.size()
            return _make_result(True, data={"width": w, "height": h})
    except Exception:
        pass
    return _make_result(False, error="无法获取屏幕尺寸")


def dispatch_action(action_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """根据动作类型分发到对应的执行函数。"""
    handler = ACTION_HANDLERS.get(action_type)
    if handler is None:
        return _make_result(
            False, error=f"不支持的动作类型: {action_type}",
        )
    return handler(params)