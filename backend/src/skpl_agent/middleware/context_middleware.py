"""
SKPL Context Middleware — Integrates context management into agent sessions.

Registered as an AgentScope MiddlewareBase, this middleware:
- on_system_prompt: Injects project anatomy, bugs, and memory context
- on_reasoning: Records token usage
- on_acting: Tracks file reads and tool outputs for waste detection
- on_compress_context: Records context changes

Implements fallback strategy: if any context operation fails, the agent
continues with an empty context injection (no-op) instead of blocking.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Awaitable, Callable, TYPE_CHECKING

from skpl_agent.context.lifecycle import (
    ContextLifecycle,
    HookContext,
    OnSessionStartHook,
    BeforeAgentInvokeHook,
    AfterAgentInvokeHook,
    OnToolCallHook,
    OnToolResultHook,
    OnErrorHook,
    OnSessionEndHook,
)
from skpl_agent.context.session_context import SessionContextConfig, SessionContextManager
from skpl_agent.context.event_emitter import ContextEventEmitter

if TYPE_CHECKING:
    from skpl_agent.agent import Agent
    from skpl_agent.model import ChatResponse

logger = logging.getLogger(__name__)


class ContextMiddleware:
    """SKPL context management middleware for AgentScope agents.

    Injects project anatomy, known bugs, and learned memories into the
    agent's context. Falls back gracefully if context management fails.

    Usage:
        agent = Agent(
            middlewares=[
                ContextMiddleware(
                    project_root="/path/to/project",
                    auto_scan=True,
                ),
            ],
        )
    """

    def __init__(
        self,
        project_root: str = ".",
        auto_scan: bool = False,
        anatomy_enabled: bool = True,
        buglog_enabled: bool = True,
        cerebrum_enabled: bool = True,
        token_tracking_enabled: bool = True,
        waste_detection_enabled: bool = True,
        token_budget: int | None = None,
        max_context_tokens: int = 8000,
        filter_sensitive: bool = True,
    ):
        self._config = SessionContextConfig(
            project_root=project_root,
            auto_scan_on_start=auto_scan,
            anatomy_enabled=anatomy_enabled,
            buglog_enabled=buglog_enabled,
            cerebrum_enabled=cerebrum_enabled,
            token_tracking_enabled=token_tracking_enabled,
            waste_detection_enabled=waste_detection_enabled,
            token_budget=token_budget,
            max_context_tokens=max_context_tokens,
            filter_sensitive=filter_sensitive,
        )
        self._session_ctx: SessionContextManager | None = None
        self._lifecycle: ContextLifecycle | None = None
        self._emitter: ContextEventEmitter | None = None

    # -- Session Lifecycle --

    async def _ensure_session(self, agent: "Agent") -> SessionContextManager:
        """Ensure a session context exists for the current agent run."""
        if self._session_ctx is None:
            session_id = getattr(agent, "session_id", None) or agent.name
            agent_id = getattr(agent, "agent_id", None) or agent.name

            self._session_ctx = SessionContextManager(
                session_id=session_id,
                agent_id=agent_id,
                config=self._config,
            )
            await self._session_ctx.initialize()

            # Setup lifecycle
            self._lifecycle = ContextLifecycle(self._session_ctx)
            self._lifecycle.register_all(self._lifecycle.create_default_hooks())

            # Setup event emitter
            self._emitter = ContextEventEmitter(agent)

            # Register compression token cost callback on the agent
            if hasattr(agent, '_compress_token_callback'):
                agent._compress_token_callback = self._on_compress_token_usage

            # Fire session start
            hook_ctx = HookContext(session_id=session_id, agent_id=agent_id)
            await self._lifecycle.fire("on_session_start", hook_ctx)

            # Emit session started event
            await self._emitter.emit_session_started(
                session_id=session_id,
                agent_id=agent_id,
                project_root=self._config.project_root,
            )

        return self._session_ctx

    # -- Middleware Hooks --

    async def on_system_prompt(self, agent: "Agent", current_prompt: str) -> str:
        """Inject SKPL context into the system prompt."""
        try:
            ctx = await self._ensure_session(agent)
            context_str = ctx.generate_context(
                include_anatomy=True,
                include_bugs=True,
                include_memory=True,
            )

            if context_str:
                # WasteDetector: skip redundant context injection
                if ctx.config.waste_detection_enabled:
                    is_redundant = ctx.waste_detector.record_context_injection(
                        ctx.session_id, context_str
                    )
                    if is_redundant:
                        logger.info(
                            "Context unchanged, skipping re-injection to save ~%d tokens",
                            len(context_str) // 4,
                        )
                        return current_prompt

                estimated_tokens = len(context_str) // 4
                if estimated_tokens > self._config.max_context_tokens:
                    logger.warning(
                        "Context too large (%d tokens), truncating",
                        estimated_tokens,
                    )

                # Emit context generated event
                if self._emitter:
                    await self._emitter.emit_context_generated(
                        session_id=ctx.session_id,
                        estimated_tokens=estimated_tokens,
                        sections=["anatomy", "bugs", "memory"],
                    )

                return f"{current_prompt}\n\n{context_str}"

        except Exception as e:
            logger.error("Context injection failed: %s, proceeding with original prompt", e)

        return current_prompt

    async def on_reasoning(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Track token usage during reasoning."""
        hook_ctx = HookContext(
            session_id=getattr(agent, "session_id", agent.name),
            agent_id=getattr(agent, "agent_id", agent.name),
        )

        try:
            async for event in next_handler():
                yield event
        except Exception as e:
            # Log error
            try:
                ctx = await self._ensure_session(agent)
                hook_ctx.error_type = type(e).__name__
                hook_ctx.error_message = str(e)
                if self._lifecycle:
                    await self._lifecycle.fire("on_error", hook_ctx)
            except Exception:
                pass
            raise

        # After reasoning succeeds
        try:
            if self._lifecycle:
                await self._lifecycle.fire("after_agent_invoke", hook_ctx)
        except Exception:
            pass

    async def on_acting(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """Track tool calls and results for waste detection."""
        tool_call = input_kwargs.get("tool_call")
        tool_name = getattr(tool_call, "name", "unknown") if tool_call else "unknown"

        hook_ctx = HookContext(
            session_id=getattr(agent, "session_id", agent.name),
            agent_id=getattr(agent, "agent_id", agent.name),
            tool_name=tool_name,
            tool_input=getattr(tool_call, "arguments", {}) if tool_call else {},
        )

        # Before tool call
        try:
            if self._lifecycle:
                await self._lifecycle.fire("on_tool_call", hook_ctx)
        except Exception:
            pass

        # Execute tool
        tool_output = ""
        async for event in next_handler():
            if hasattr(event, "content"):
                tool_output += str(event.content)
            yield event

        # After tool result
        try:
            if self._lifecycle:
                hook_ctx.tool_output = tool_output
                await self._lifecycle.fire("on_tool_result", hook_ctx)
        except Exception:
            pass

    async def on_model_call(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., Awaitable["ChatResponse"]],
    ) -> "ChatResponse":
        """Track token usage from model calls."""
        response = await next_handler()

        # Record token usage
        try:
            ctx = await self._ensure_session(agent)
            usage = getattr(response, "usage", None)
            if usage:
                input_tokens = getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0)
                output_tokens = getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0)
                ctx.record_token_usage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model_name=getattr(response, "model", None),
                )
        except Exception:
            pass

        return response

    # -- Compression Token Tracking --

    def _on_compress_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model_name: str | None = None,
    ) -> None:
        """Callback invoked by Agent after context compression LLM call.

        Records the token cost of compression in the token ledger so the
        compression overhead is properly accounted for in the budget.
        """
        if self._session_ctx:
            self._session_ctx.record_token_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=model_name,
            )

    # -- Compression Middleware (WasteDetector Integration) --

    async def on_compress_context(
        self,
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., Awaitable[None]],
    ) -> None:
        """Middleware hook for context compression — integrates WasteDetector.

        Before compression:
        - Checks waste detector for detected patterns
        - Marks wasteful tokens in the ledger

        After compression:
        - Records context size change
        - Checks if new context is oversized
        """
        # Pre-compression: check waste patterns
        if self._session_ctx and self._session_ctx.config.waste_detection_enabled:
            waste_patterns = self._session_ctx.waste_detector.get_patterns()
            total_waste = self._session_ctx.waste_detector.get_total_waste()
            if total_waste > 0 and waste_patterns:
                waste_summary = self._session_ctx.waste_detector.get_waste_summary()
                logger.info(
                    "WasteDetector: %d patterns found before compression, "
                    "%d tokens wasted: %s",
                    len(waste_patterns),
                    total_waste,
                    waste_summary,
                )
                # Mark wasted tokens in ledger
                self._session_ctx.record_token_usage(
                    input_tokens=total_waste,
                    output_tokens=0,
                    is_waste=True,
                    waste_reason="; ".join(
                        f"{p.pattern_type}: {p.description[:100]}"
                        for p in waste_patterns[:5]
                    ),
                )

        # Execute the actual compression
        await next_handler()

        # Post-compression: check if new context is still oversized
        if self._session_ctx and self._session_ctx.config.waste_detection_enabled:
            context_str = self._session_ctx.generate_context(
                include_anatomy=False,
                include_bugs=False,
                include_memory=False,
            )
            if context_str:
                self._session_ctx.waste_detector.check_context_size(
                    context_str,
                    self._config.max_context_tokens,
                )

    # -- Cleanup --

    async def cleanup(self) -> None:
        """Clean up session resources."""
        if self._session_ctx:
            if self._lifecycle:
                hook_ctx = HookContext(
                    session_id=self._session_ctx.session_id,
                    agent_id=self._session_ctx.agent_id,
                )
                try:
                    await self._lifecycle.fire("on_session_end", hook_ctx)
                except Exception:
                    pass

            # Emit session ended event
            if self._emitter:
                try:
                    await self._emitter.emit_session_ended(
                        session_id=self._session_ctx.session_id,
                        agent_id=self._session_ctx.agent_id,
                        stats={
                            "anatomy": self._session_ctx.anatomy_store.get_stats() if self._session_ctx.anatomy_store else {},
                            "bugs": self._session_ctx.buglog.get_stats() if self._session_ctx.buglog else {},
                            "memory": self._session_ctx.cerebrum.get_stats() if self._session_ctx.cerebrum else {},
                            "tokens": self._session_ctx.token_ledger.get_summary() if self._session_ctx.token_ledger else {},
                        },
                    )
                except Exception:
                    pass

            self._session_ctx.shutdown()
            self._session_ctx = None
            self._lifecycle = None
            self._emitter = None

    async def get_middleware_key(self) -> str:
        return "skpl_context_middleware"

    def is_implemented(self, method_name: str) -> bool:
        """Check if a middleware hook method is implemented."""
        return hasattr(self, method_name) and callable(getattr(self, method_name))