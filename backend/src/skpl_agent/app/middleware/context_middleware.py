"""Context middleware — registers lifecycle hooks as AgentScope middleware.

This middleware bridges the OpenWolf context subsystem (lifecycle hooks,
token tracking, bug logging) into the AgentScope agent invocation pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from skpl_agent.context.lifecycle import (
    AfterAgentInvokeHook,
    BeforeAgentInvokeHook,
    ContextLifecycle,
    OnErrorHook,
    OnSessionEndHook,
    OnSessionStartHook,
    OnToolCallHook,
    OnToolResultHook,
)

if TYPE_CHECKING:
    from skpl_agent.context.session_context import SessionContextManager

logger = logging.getLogger(__name__)


class ContextMiddleware:
    """AgentScope middleware that injects context lifecycle hooks.

    Each hook is called at the appropriate point in the agent invocation
    cycle, providing context injection, tracking, and error logging.
    """

    def __init__(
        self,
        session_context: SessionContextManager | None = None,
        *,
        enable_token_tracking: bool = True,
        enable_bug_logging: bool = True,
        enable_anatomy_injection: bool = True,
    ) -> None:
        self._session_context = session_context
        self._enable_token_tracking = enable_token_tracking
        self._enable_bug_logging = enable_bug_logging
        self._enable_anatomy_injection = enable_anatomy_injection
        self._lifecycle = ContextLifecycle()

    async def on_session_start(self, session_id: str, agent_id: str | None = None) -> None:
        """Called when a new agent session starts."""
        if not self._session_context:
            return
        logger.debug("Context middleware: session_start %s", session_id)

        if self._enable_anatomy_injection:
            anatomy = self._session_context.anatomy
            if anatomy and anatomy.anatomy_text:
                logger.info("Context middleware: injecting anatomy (%d chars)", len(anatomy.anatomy_text))

    async def on_before_agent_invoke(self, session_id: str, messages: list[Any]) -> list[Any]:
        """Called before the agent processes messages.

        Can inject context into the message list.
        """
        if not self._session_context:
            return messages

        logger.debug("Context middleware: before_agent_invoke %s", session_id)

        if self._enable_anatomy_injection:
            anatomy = self._session_context.anatomy
            if anatomy and anatomy.anatomy_text:
                # Inject anatomy as system context
                context_msg = {
                    "role": "system",
                    "content": f"[Project Context]\n{anatomy.anatomy_text}",
                }
                messages = [context_msg] + list(messages)

        return messages

    async def on_after_agent_invoke(self, session_id: str, response: Any) -> None:
        """Called after the agent produces a response."""
        if not self._session_context:
            return

        logger.debug("Context middleware: after_agent_invoke %s", session_id)

        if self._enable_token_tracking:
            token_ledger = self._session_context.token_ledger
            if token_ledger:
                try:
                    # Extract token usage from response if available
                    usage = getattr(response, "usage", None) or getattr(response, "usage_metadata", None)
                    if usage:
                        input_tokens = getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0)
                        output_tokens = getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0)
                        if input_tokens or output_tokens:
                            token_ledger.record(
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                model=getattr(response, "model", "unknown"),
                            )
                except Exception:
                    logger.debug("Context middleware: failed to extract token usage", exc_info=True)

    async def on_tool_call(self, session_id: str, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Called when the agent invokes a tool."""
        logger.debug("Context middleware: tool_call %s -> %s", session_id, tool_name)

    async def on_tool_result(self, session_id: str, tool_name: str, result: Any) -> None:
        """Called when a tool returns a result."""
        logger.debug("Context middleware: tool_result %s <- %s", session_id, tool_name)

    async def on_error(self, session_id: str, error: Exception) -> None:
        """Called when an error occurs during agent execution."""
        if not self._session_context or not self._enable_bug_logging:
            return

        logger.debug("Context middleware: error in %s: %s", session_id, error)

        try:
            buglog = self._session_context.buglog
            if buglog:
                buglog.log(
                    error_type=type(error).__name__,
                    error_message=str(error),
                    file_path=None,
                    line_number=None,
                )
        except Exception:
            logger.debug("Context middleware: failed to log bug", exc_info=True)

    async def on_session_end(self, session_id: str) -> None:
        """Called when a session ends."""
        logger.debug("Context middleware: session_end %s", session_id)

        if self._session_context:
            try:
                self._session_context.shutdown()
            except Exception:
                logger.debug("Context middleware: failed to shutdown session context", exc_info=True)