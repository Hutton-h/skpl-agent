"""Desktop grounding middleware — injects UI grounding into agent pipelines.

This middleware intercepts agent messages, detects screenshots, and
optionally adds UI element grounding information to the context.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from skpl_agent.desktop_node.grounding import (
    GroundingModel,
    GroundingResult,
    SimpleGrounding,
)

logger = logging.getLogger(__name__)


class GroundingMiddleware(BaseHTTPMiddleware):
    """Middleware that adds UI grounding to agent messages.

    When a message contains a screenshot (base64 image), this middleware
    can optionally:
    1. Detect UI elements using the grounding model
    2. Annotate the screenshot with bounding boxes
    3. Add element descriptions to the message context

    Usage:
        >>> grounding = GroundingMiddleware(app)
        >>> msg = {"screenshot": base64_image, "text": "click the button"}
        >>> enriched = await grounding.process(msg)
        >>> print(enriched["grounding_elements"])  # list of detected elements
    """

    def __init__(
        self,
        app: Any,
        model: Optional[GroundingModel] = None,
        auto_ground: bool = False,
        max_elements: int = 50,
        min_confidence: float = 0.3,
        annotate_screenshots: bool = True,
    ) -> None:
        super().__init__(app)
        self._model = model or SimpleGrounding()
        self._auto_ground = auto_ground
        self._max_elements = max_elements
        self._min_confidence = min_confidence
        self._annotate_screenshots = annotate_screenshots

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Pass-through dispatch — grounding is applied at the agent pipeline level."""
        return await call_next(request)

    @property
    def auto_ground(self) -> bool:
        return self._auto_ground

    @auto_ground.setter
    def auto_ground(self, value: bool) -> None:
        self._auto_ground = value

    # ── Processing ───────────────────────────────────────────────────────

    async def process(self, message: dict[str, Any]) -> dict[str, Any]:
        """Process a message, optionally adding grounding information.

        Args:
            message: Agent message dict. May contain 'screenshot' key with
                     base64-encoded image data.

        Returns:
            Enriched message dict with grounding_elements added.
        """
        screenshot = message.get("screenshot")
        if not screenshot:
            return message

        # Check if auto-grounding is enabled
        if not self._auto_ground and not message.get("request_grounding"):
            return message

        try:
            instruction = message.get("text", "") or message.get("instruction", "")
            result = await self._ground(screenshot, instruction)

            # Filter by confidence
            elements = [
                e for e in result.elements
                if e.get("confidence", 1.0) >= self._min_confidence
            ][:self._max_elements]

            # Add grounding info to message
            message["grounding_elements"] = elements
            message["grounding_element_count"] = len(elements)
            message["grounding_model"] = result.model_used
            message["grounding_latency_ms"] = result.latency_ms

            if self._annotate_screenshots and result.annotated_image_base64:
                message["annotated_screenshot"] = result.annotated_image_base64

            # Add element descriptions as text
            if elements:
                descriptions = self._format_elements(elements)
                existing_text = message.get("text", "")
                message["text"] = (
                    f"{existing_text}\n\n[UI Elements Detected]\n{descriptions}"
                ).strip()

            logger.debug(
                "Grounding: %d elements found (%.0fms)",
                len(elements), result.latency_ms,
            )

        except Exception as e:
            logger.error("Grounding middleware error: %s", e)
            message["grounding_error"] = str(e)

        return message

    async def ground_screenshot(
        self,
        screenshot_base64: str,
        instruction: str = "",
    ) -> GroundingResult:
        """Explicitly ground a screenshot.

        Args:
            screenshot_base64: Base64-encoded screenshot.
            instruction: Optional grounding instruction.

        Returns:
            GroundingResult with detected elements.
        """
        return await self._ground(screenshot_base64, instruction)

    # ── Internal ─────────────────────────────────────────────────────────

    async def _ground(
        self, screenshot: str, instruction: str,
    ) -> GroundingResult:
        """Run grounding on a screenshot."""
        # Handle both raw base64 and data URIs
        if screenshot.startswith("data:"):
            # Extract base64 from data URI
            screenshot = screenshot.split(",", 1)[1]

        return self._model.ground(
            image_base64=screenshot,
            instruction=instruction,
        )

    @staticmethod
    def _format_elements(elements: list[dict[str, Any]]) -> str:
        """Format grounded elements as human-readable text."""
        lines: list[str] = []
        for i, elem in enumerate(elements):
            label = elem.get("label", f"element_{i}")
            bbox = elem.get("bbox", [])
            confidence = elem.get("confidence", 1.0)
            elem_type = elem.get("type", "unknown")

            if len(bbox) == 4:
                lines.append(
                    f"  [{i}] {label} ({elem_type}, "
                    f"confidence={confidence:.2f}, "
                    f"bbox=[{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}])"
                )
            else:
                lines.append(
                    f"  [{i}] {label} ({elem_type}, confidence={confidence:.2f})"
                )

        return "\n".join(lines)

    def unload(self) -> None:
        """Unload the grounding model."""
        self._model.unload()


class DesktopContextMiddleware:
    """Middleware that enriches agent context with desktop state.

    Adds current desktop state (active app, screen info, available actions)
    to the agent's context before each turn.
    """

    def __init__(self, desktop_agent=None) -> None:
        self._agent = desktop_agent

    def set_agent(self, agent) -> None:
        """Set the desktop agent reference."""
        self._agent = agent

    async def enrich_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Add desktop context to the agent's context.

        Args:
            context: Current agent context dict.

        Returns:
            Enriched context with desktop state.
        """
        if self._agent is None:
            return context

        try:
            # Get current desktop state
            tree = await self._agent.extract_tree()
            top_app = await self._agent.get_top_app()

            context["desktop_state"] = {
                "top_app": top_app,
                "ui_tree": tree,
                "screen_size": [
                    self._agent.state.screen_width,
                    self._agent.state.screen_height,
                ],
                "available_actions": [
                    "click", "double_click", "right_click",
                    "type_text", "hotkey", "scroll", "drag",
                    "open_app", "switch_app", "wait",
                    "screenshot", "extract_tree",
                ],
            }

            logger.debug("Desktop context enriched: top_app=%s", top_app)

        except Exception as e:
            logger.error("Failed to enrich desktop context: %s", e)
            context["desktop_state"] = {"error": str(e)}

        return context