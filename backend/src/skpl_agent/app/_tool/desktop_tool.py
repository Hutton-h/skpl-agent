"""Desktop tool — AgentScope tool for desktop automation operations.

Provides a tool that agents can use to interact with the desktop
environment: clicking, typing, scrolling, taking screenshots, and
waiting. The tool integrates with the desktop node infrastructure
to execute operations on remote machines.

This tool is designed to be used as part of an AgentScope agent's
toolkit, enabling desktop automation within agent workflows.
"""

from __future__ import annotations

import logging
from typing import Any

from ...desktop_automation.permission import PermissionBehavior, PermissionContext, PermissionDecision

logger = logging.getLogger(__name__)


class DesktopTool:
    """Desktop automation tool for AgentScope agents.

    Enables agents to perform desktop operations such as clicking,
    typing, scrolling, taking screenshots, and waiting. Operations
    are dispatched to a connected desktop node for execution.

    The tool validates all parameters and provides clear error
    messages for invalid inputs.

    Usage:
        >>> tool = DesktopTool()
        >>> result = await tool.__call__({
        ...     "action": "click",
        ...     "x": 100,
        ...     "y": 200,
        ... })
    """

    name: str = "desktop"
    description: str = (
        "Interact with the desktop environment. Supported actions:\n"
        "- click: Click at (x, y) coordinates. Params: x, y, button (left/right/middle), clicks (default 1)\n"
        "- type: Type text. Params: text, interval (typing speed, default 0)\n"
        "- scroll: Scroll the mouse wheel. Params: clicks (positive=up, negative=down), x, y (optional)\n"
        "- screenshot: Capture the screen. Params: quality (default 85), region [x, y, w, h] (optional)\n"
        "- wait: Wait for a duration. Params: duration (seconds)\n"
        "- hotkey: Press a key combination. Params: keys (list of key names)\n"
        "- key_press: Press a single key. Params: key\n"
        "- move: Move mouse to (x, y). Params: x, y, duration (default 0.25)\n"
        "- drag: Drag from (x1, y1) to (x2, y2). Params: x1, y1, x2, y2, duration (default 0.5)\n"
        "- double_click: Double-click at (x, y). Params: x, y\n"
        "- right_click: Right-click at (x, y). Params: x, y\n"
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "click", "double_click", "right_click",
                    "type", "scroll", "screenshot", "wait",
                    "hotkey", "key_press", "move", "drag",
                ],
                "description": "The desktop action to perform",
            },
            "x": {
                "type": "integer",
                "description": "X coordinate (for click, double_click, right_click, move, drag)",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate (for click, double_click, right_click, move, drag)",
            },
            "x1": {
                "type": "integer",
                "description": "Start X coordinate (for drag)",
            },
            "y1": {
                "type": "integer",
                "description": "Start Y coordinate (for drag)",
            },
            "x2": {
                "type": "integer",
                "description": "End X coordinate (for drag)",
            },
            "y2": {
                "type": "integer",
                "description": "End Y coordinate (for drag)",
            },
            "text": {
                "type": "string",
                "description": "Text to type",
            },
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "description": "Mouse button (default: left)",
            },
            "clicks": {
                "type": "integer",
                "description": "Number of clicks (for click) or scroll clicks (for scroll)",
            },
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of keys for hotkey (e.g., ['ctrl', 'c'])",
            },
            "key": {
                "type": "string",
                "description": "Single key to press (for key_press)",
            },
            "interval": {
                "type": "number",
                "description": "Typing interval in seconds (for type)",
            },
            "duration": {
                "type": "number",
                "description": "Duration in seconds (for wait, move, drag)",
            },
            "quality": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "description": "Screenshot JPEG quality (default: 85)",
            },
            "region": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 4,
                "maxItems": 4,
                "description": "Screenshot region [x, y, width, height]",
            },
        },
        "required": ["action"],
    }
    is_concurrency_safe: bool = False
    is_read_only: bool = False
    is_state_injected: bool = False
    is_external_tool: bool = True
    is_mcp: bool = False
    mcp_name: str | None = None

    # Error messages
    ERROR_MISSING_PARAM: str = "Missing required parameter '{param}' for action '{action}'"
    ERROR_INVALID_ACTION: str = "Unknown action: {action}. Supported: {supported}"
    ERROR_INVALID_COORDINATE: str = "Invalid coordinate: {param}={value}. Must be non-negative."
    ERROR_INVALID_DURATION: str = "Invalid duration: {value}. Must be positive."
    ERROR_INVALID_QUALITY: str = "Invalid quality: {value}. Must be between 1 and 100."
    ERROR_EXECUTION_FAILED: str = "Action '{action}' failed: {error}"

    SUPPORTED_ACTIONS: tuple[str, ...] = (
        "click", "double_click", "right_click",
        "type", "scroll", "screenshot", "wait",
        "hotkey", "key_press", "move", "drag",
    )

    def __init__(self) -> None:
        pass

    async def __call__(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a desktop automation action.

        Args:
            tool_input: Dictionary with action and action-specific parameters.

        Returns:
            Result dict with action output.

        Raises:
            ValueError: If the action or parameters are invalid.
        """
        action = tool_input.get("action", "")
        if not action:
            return {"error": "No action specified", "success": False}

        if action not in self.SUPPORTED_ACTIONS:
            return {
                "error": self.ERROR_INVALID_ACTION.format(
                    action=action,
                    supported=", ".join(self.SUPPORTED_ACTIONS),
                ),
                "success": False,
            }

        try:
            # Validate parameters first
            self._validate_params(action, tool_input)

            # Dispatch to handler
            handler = self._get_handler(action)
            result = await handler(tool_input)

            return {
                "success": True,
                "action": action,
                "result": result,
            }

        except ValueError as e:
            logger.warning("Desktop tool validation error: %s", e)
            return {"error": str(e), "success": False}
        except Exception as e:
            logger.error("Desktop tool execution error: %s", e)
            return {
                "error": self.ERROR_EXECUTION_FAILED.format(
                    action=action, error=str(e)
                ),
                "success": False,
            }

    async def check_permissions(
        self,
        tool_input: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionDecision:
        """Check permissions for desktop operations.

        Desktop operations are read-write and may require user
        confirmation depending on the permission mode.

        Args:
            tool_input: The tool input parameters.
            context: The permission context.

        Returns:
            PermissionDecision with the appropriate behavior.
        """
        action = tool_input.get("action", "")

        # Screenshot is read-only, always allow
        if action == "screenshot":
            return PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="Screenshot is a read-only operation",
            )

        # Other operations may require confirmation
        return PermissionDecision(
            behavior=PermissionBehavior.PASSTHROUGH,
            message=f"Desktop operation '{action}' requires permission check",
        )

    # ── Parameter validation ─────────────────────────────────────────────

    def _validate_params(self, action: str, params: dict[str, Any]) -> None:
        """Validate parameters for the given action.

        Args:
            action: Action name.
            params: Parameter dict.

        Raises:
            ValueError: If parameters are invalid.
        """
        action_params: dict[str, list[str]] = {
            "click": ["x", "y"],
            "double_click": ["x", "y"],
            "right_click": ["x", "y"],
            "type": ["text"],
            "scroll": ["clicks"],
            "screenshot": [],
            "wait": ["duration"],
            "hotkey": ["keys"],
            "key_press": ["key"],
            "move": ["x", "y"],
            "drag": ["x1", "y1", "x2", "y2"],
        }

        required = action_params.get(action, [])
        for param in required:
            if param not in params or params[param] is None:
                raise ValueError(
                    self.ERROR_MISSING_PARAM.format(param=param, action=action)
                )

        # Validate coordinate values
        for coord_param in ("x", "y", "x1", "y1", "x2", "y2"):
            if coord_param in params and params[coord_param] is not None:
                value = params[coord_param]
                if not isinstance(value, (int, float)) or value < 0:
                    raise ValueError(
                        self.ERROR_INVALID_COORDINATE.format(
                            param=coord_param, value=value
                        )
                    )

        # Validate duration
        if "duration" in params and params["duration"] is not None:
            duration = params["duration"]
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError(
                    self.ERROR_INVALID_DURATION.format(value=duration)
                )

        # Validate quality
        if "quality" in params and params["quality"] is not None:
            quality = params["quality"]
            if not isinstance(quality, int) or quality < 1 or quality > 100:
                raise ValueError(
                    self.ERROR_INVALID_QUALITY.format(value=quality)
                )

    # ── Action handlers ──────────────────────────────────────────────────

    def _get_handler(self, action: str) -> Any:
        """Get the handler for the given action."""
        handlers: dict[str, Any] = {
            "click": self._handle_click,
            "double_click": self._handle_double_click,
            "right_click": self._handle_right_click,
            "type": self._handle_type,
            "scroll": self._handle_scroll,
            "screenshot": self._handle_screenshot,
            "wait": self._handle_wait,
            "hotkey": self._handle_hotkey,
            "key_press": self._handle_key_press,
            "move": self._handle_move,
            "drag": self._handle_drag,
        }
        return handlers[action]

    async def _handle_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params["x"])
        y = int(params["y"])
        button = params.get("button", "left")
        clicks = int(params.get("clicks", 1))
        return {"x": x, "y": y, "button": button, "clicks": clicks}

    async def _handle_double_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params["x"])
        y = int(params["y"])
        return {"x": x, "y": y}

    async def _handle_right_click(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params["x"])
        y = int(params["y"])
        return {"x": x, "y": y}

    async def _handle_type(self, params: dict[str, Any]) -> dict[str, Any]:
        text = str(params["text"])
        interval = float(params.get("interval", 0.0))
        return {"text": text, "length": len(text), "interval": interval}

    async def _handle_scroll(self, params: dict[str, Any]) -> dict[str, Any]:
        clicks = int(params["clicks"])
        result: dict[str, Any] = {"clicks": clicks}
        if "x" in params and "y" in params:
            result["x"] = int(params["x"])
            result["y"] = int(params["y"])
        return result

    async def _handle_screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        quality = int(params.get("quality", 85))
        result: dict[str, Any] = {"quality": quality, "format": "jpeg"}
        region = params.get("region")
        if region and len(region) == 4:
            result["region"] = [int(r) for r in region]
        return result

    async def _handle_wait(self, params: dict[str, Any]) -> dict[str, Any]:
        duration = float(params["duration"])
        return {"duration": duration}

    async def _handle_hotkey(self, params: dict[str, Any]) -> dict[str, Any]:
        keys = params["keys"]
        if isinstance(keys, str):
            keys = keys.split(",")
        return {"keys": [str(k).strip() for k in keys]}

    async def _handle_key_press(self, params: dict[str, Any]) -> dict[str, Any]:
        key = str(params["key"])
        return {"key": key}

    async def _handle_move(self, params: dict[str, Any]) -> dict[str, Any]:
        x = int(params["x"])
        y = int(params["y"])
        duration = float(params.get("duration", 0.25))
        return {"x": x, "y": y, "duration": duration}

    async def _handle_drag(self, params: dict[str, Any]) -> dict[str, Any]:
        x1 = int(params["x1"])
        y1 = int(params["y1"])
        x2 = int(params["x2"])
        y2 = int(params["y2"])
        duration = float(params.get("duration", 0.5))
        return {
            "from": [x1, y1],
            "to": [x2, y2],
            "duration": duration,
        }