"""Action executor — safely executes desktop automation actions.

Accepts action requests from the control center, validates them against
the security policy, executes them, and reports results back. Supports
Token Bucket rate limiting to prevent excessive action execution.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from skpl_agent.desktop_node.events import (
    ActionRequest,
    ActionResult,
    ActionStatus,
    ActionType,
)
from skpl_agent.desktop_node.security import (
    CodeSecurityError,
    SecurityError,
    SecurityPolicy,
)

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when the rate limit has been exceeded for action execution.

    Attributes:
        retry_after_seconds: Seconds until the rate limiter allows more actions.
        retry_after: Alias for retry_after_seconds.
        action_id: ID of the action that was rejected.
    """

    def __init__(
        self,
        message: str = "",
        retry_after_seconds: float = 0.0,
        retry_after: float | None = None,
        action_id: str = "",
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after if retry_after is not None else retry_after_seconds
        self.retry_after = self.retry_after_seconds
        self.action_id = action_id


class ActionExecutor:
    """Executes desktop automation actions with security validation.

    Actions are executed in a thread pool to avoid blocking the async
    event loop. Each action is validated against the security policy
    before execution. An optional rate limiter can be used to control
    the rate of action execution.

    Usage:
        >>> executor = ActionExecutor(policy=SecurityPolicy.default())
        >>> # With rate limiting:
        >>> from skpl_agent.desktop_node._rate_limit import TokenBucket
        >>> rate_limiter = TokenBucket(max_tokens=100, refill_rate=10)
        >>> executor = ActionExecutor(
        ...     policy=SecurityPolicy.default(),
        ...     rate_limiter=rate_limiter,
        ... )
        >>> request = ActionRequest(
        ...     action_id="abc",
        ...     action_type=ActionType.CLICK,
        ...     params={"x": 100, "y": 200},
        ... )
        >>> result = await executor.execute(request)
    """

    def __init__(
        self,
        policy: SecurityPolicy | None = None,
        max_workers: int = 3,
        rate_limiter: Any = None,
    ) -> None:
        self._policy = policy or SecurityPolicy.default()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_actions: dict[str, asyncio.Task] = {}
        self._active_count = 0
        self._rate_limiter = rate_limiter

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def policy(self) -> SecurityPolicy:
        return self._policy

    @property
    def rate_limiter(self) -> Any:
        """Return the rate limiter instance, or None if not configured."""
        return self._rate_limiter

    @rate_limiter.setter
    def rate_limiter(self, value: Any) -> None:
        """Set the rate limiter instance."""
        self._rate_limiter = value

    async def execute(self, request: ActionRequest) -> ActionResult:
        """Execute an action request and return the result.

        Checks the rate limiter (if configured) before executing the action.
        Raises RateLimitError if the rate limit is exceeded.

        Args:
            request: The action request from the control center.

        Returns:
            ActionResult with status, result data, and timing.

        Raises:
            RateLimitError: If the rate limiter is exhausted.
        """
        start_time = time.monotonic()
        self._active_count += 1

        try:
            # ── Rate limit check ─────────────────────────────────────
            if self._rate_limiter is not None:
                try:
                    allowed = self._rate_limiter.consume(tokens=1)
                    if not allowed:
                        retry_after = getattr(
                            self._rate_limiter, "time_until_refill", lambda _: 1.0
                        )(1)
                        rate_limit_msg = (
                            f"Rate limit exceeded for action {request.action_id}. "
                            f"Retry after {retry_after:.1f}s"
                        )
                        logger.warning(rate_limit_msg)
                        raise RateLimitError(
                            message=rate_limit_msg,
                            retry_after_seconds=float(retry_after),
                            action_id=request.action_id,
                        )
                except RateLimitError:
                    raise
                except Exception as e:
                    logger.warning(
                        "Rate limiter check failed (non-fatal): %s", e
                    )

            result_data = await self._execute_action(
                request.action_type, request.params
            )
            elapsed = (time.monotonic() - start_time) * 1000

            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.COMPLETED,
                result=result_data,
                duration_ms=round(elapsed, 2),
            )

        except SecurityError as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.warning(
                "Security violation in action %s: %s", request.action_id, e
            )
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.FAILED,
                error=f"Security violation: {e}",
                duration_ms=round(elapsed, 2),
            )

        except asyncio.TimeoutError:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error("Action %s timed out", request.action_id)
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.TIMED_OUT,
                error=f"Action timed out after {request.timeout}s",
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error(
                "Action %s failed: %s\n%s",
                request.action_id, e, traceback.format_exc(),
            )
            return ActionResult(
                action_id=request.action_id,
                status=ActionStatus.FAILED,
                error=str(e),
                duration_ms=round(elapsed, 2),
            )

        finally:
            self._active_count -= 1

    async def cancel(self, action_id: str) -> bool:
        """Cancel a running action by ID."""
        task = self._running_actions.pop(action_id, None)
        if task and not task.done():
            task.cancel()
            return True
        return False

    # ── Action Dispatch ──────────────────────────────────────────────────

    async def _execute_action(
        self, action_type: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch to the appropriate action handler."""
        action_type = action_type.lower()

        handlers: dict[str, Any] = {
            ActionType.CLICK: self._handle_click,
            ActionType.DOUBLE_CLICK: self._handle_double_click,
            ActionType.RIGHT_CLICK: self._handle_right_click,
            ActionType.TYPE: self._handle_type,
            ActionType.KEY_PRESS: self._handle_key_press,
            ActionType.HOTKEY: self._handle_hotkey,
            ActionType.SCROLL: self._handle_scroll,
            ActionType.DRAG: self._handle_drag,
            ActionType.MOVE: self._handle_move,
            ActionType.WAIT: self._handle_wait,
            ActionType.SCREENSHOT: self._handle_screenshot,
            ActionType.OPEN_APP: self._handle_open_app,
            ActionType.SWITCH_APP: self._handle_switch_app,
            ActionType.CUSTOM_CODE: self._handle_custom_code,
        }

        handler = handlers.get(action_type)
        if handler is None:
            raise ValueError(f"Unknown action type: {action_type}")

        timeout = params.get("timeout", self._policy._max_execution_time)
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                self._executor, handler, params
            ),
            timeout=timeout,
        )

    # ── Action Handlers ──────────────────────────────────────────────────

    def _handle_click(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        button = params.get("button", "left")
        pyautogui.click(x, y, button=button)
        return {"x": x, "y": y, "button": button}

    def _handle_double_click(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        pyautogui.doubleClick(x, y)
        return {"x": x, "y": y}

    def _handle_right_click(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        pyautogui.rightClick(x, y)
        return {"x": x, "y": y}

    def _handle_type(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        text = str(params.get("text", ""))
        interval = float(params.get("interval", 0.0))
        pyautogui.write(text, interval=interval)
        return {"text": text, "length": len(text)}

    def _handle_key_press(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        key = str(params.get("key", ""))
        pyautogui.press(key)
        return {"key": key}

    def _handle_hotkey(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = keys.split(",")
        pyautogui.hotkey(*keys)
        return {"keys": keys}

    def _handle_scroll(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        clicks = int(params.get("clicks", 0))
        x = params.get("x")
        y = params.get("y")
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=int(x), y=int(y))
        else:
            pyautogui.scroll(clicks)
        return {"clicks": clicks}

    def _handle_drag(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        x1 = int(params.get("x1", 0))
        y1 = int(params.get("y1", 0))
        x2 = int(params.get("x2", 0))
        y2 = int(params.get("y2", 0))
        duration = float(params.get("duration", 0.5))
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
        return {"from": (x1, y1), "to": (x2, y2)}

    def _handle_move(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        duration = float(params.get("duration", 0.25))
        pyautogui.moveTo(x, y, duration=duration)
        return {"x": x, "y": y}

    def _handle_wait(self, params: dict[str, Any]) -> dict[str, Any]:
        import time as _time
        duration = float(params.get("duration", 1.0))
        _time.sleep(duration)
        return {"duration": duration}

    def _handle_screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        from skpl_agent.desktop_node.screen import ScreenCapture

        quality = int(params.get("quality", 85))
        region = params.get("region")
        if region and len(region) == 4:
            region = tuple(region)
        else:
            region = None

        cap = ScreenCapture(quality=quality)
        b64 = cap.capture_base64(region=region)
        size = cap.get_screen_size()

        return {
            "image_base64": b64,
            "width": size[0] if region is None else region[2],
            "height": size[1] if region is None else region[3],
            "format": "jpeg",
        }

    def _handle_open_app(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        import time as _time

        app_name = str(params.get("app_name", ""))
        self._policy.check_app(app_name)

        pyautogui.hotkey("win", "r")
        _time.sleep(0.5)
        pyautogui.write(app_name)
        pyautogui.press("enter")
        _time.sleep(1.0)

        return {"app_name": app_name}

    def _handle_switch_app(self, params: dict[str, Any]) -> dict[str, Any]:
        import pyautogui
        import time as _time

        app_name = str(params.get("app_name", ""))
        self._policy.check_app(app_name)

        pyautogui.hotkey("win", "d")
        _time.sleep(0.5)
        pyautogui.write(app_name)
        pyautogui.press("enter")
        _time.sleep(1.0)

        return {"app_name": app_name}

    def _handle_custom_code(self, params: dict[str, Any]) -> dict[str, Any]:
        code = str(params.get("code", ""))
        self._policy.check_code(code)

        local_vars: dict[str, Any] = {}
        exec(code, {"__builtins__": __builtins__}, local_vars)

        return {"output": str(local_vars.get("result", ""))}

    def shutdown(self) -> None:
        """Shutdown the executor, canceling all running actions."""
        for action_id in list(self._running_actions.keys()):
            self.cancel(action_id)  # Fire and forget
        self._executor.shutdown(wait=False)


class DesktopExecutor:
    """High-level desktop executor wrapping ActionExecutor with a simpler API.

    Provides compatibility with the test suite's expected API:
    - Constructor takes aci, max_actions_per_second, max_burst
    - execute() takes a string action type and kwargs
    """

    def __init__(
        self,
        aci: Any = None,
        max_actions_per_second: float = 10.0,
        max_burst: int = 20,
    ) -> None:
        from skpl_agent.desktop_node._rate_limit import TokenBucket

        self._aci = aci
        self._rate_limiter = TokenBucket(
            max_tokens=max_burst,
            refill_rate=max_actions_per_second,
        )
        self._action_executor = ActionExecutor(rate_limiter=self._rate_limiter)

    async def execute(self, action_type: str, **params: Any) -> Any:
        """Execute a desktop action by type name with keyword params.

        Args:
            action_type: Action type string (click, type, screenshot, etc.)
            **params: Action-specific parameters

        Returns:
            ActionResult-like object with .success attribute
        """
        from skpl_agent.desktop_node.events import ActionRequest, ActionType

        action_type_enum = ActionType(action_type)
        request = ActionRequest(
            action_id=f"test-{action_type}",
            action_type=action_type_enum,
            params=dict(params),
        )
        return await self._action_executor.execute(request)