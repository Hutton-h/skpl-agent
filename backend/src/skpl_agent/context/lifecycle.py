"""
Context Lifecycle — Hooks for injecting context into the agent pipeline.

Defines 7 lifecycle hooks that fire at specific points during agent
execution. Each hook can modify the context or take side effects
like logging, scanning, or memory updates.

Based on OpenWolf's lifecycle hook system, rewritten in Python with
fallback strategies for graceful degradation.

Hooks:
  1. on_session_start    — Initialize context, run anatomy scan
  2. before_agent_invoke — Inject context into agent prompt
  3. after_agent_invoke  — Extract learnings, update memory
  4. on_tool_call        — Record tool usage, waste detection
  5. on_tool_result      — Record tool result, detect duplicates
  6. on_error            — Log bug, update error memory
  7. on_session_end      — Persist state, generate summary
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from skpl_agent.context.anatomy_scanner import ScanMode, ScanResult
from skpl_agent.context.session_context import SessionContextConfig, SessionContextManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hook Context
# ---------------------------------------------------------------------------


@dataclass
class HookContext:
    """Data passed to lifecycle hooks."""

    session_id: str
    agent_id: str | None = None
    # Agent invocation
    system_prompt: str | None = None
    user_message: str | None = None
    agent_response: str | None = None
    # Tool calls
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: str | None = None
    # Error
    error_type: str | None = None
    error_message: str | None = None
    error_traceback: str | None = None
    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str | None = None
    # Arbitrary metadata
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lifecycle Hook Interface
# ---------------------------------------------------------------------------


class LifecycleHook(ABC):
    """Base class for lifecycle hooks with fallback support."""

    fallback_enabled: bool = True
    name: str = "base"

    @abstractmethod
    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        """Execute the hook. Must not raise exceptions."""
        ...

    async def execute_safe(
        self, ctx: SessionContextManager, hook_ctx: HookContext
    ) -> bool:
        """Execute with fallback. Returns True on success, False on failure."""
        try:
            await self.execute(ctx, hook_ctx)
            return True
        except Exception as e:
            logger.error(
                "Lifecycle hook '%s' failed: %s. Fallback: %s",
                self.name,
                e,
                "enabled" if self.fallback_enabled else "disabled",
            )
            if self.fallback_enabled:
                await self._fallback(ctx, hook_ctx)
            return False

    async def _fallback(
        self, ctx: SessionContextManager, hook_ctx: HookContext
    ) -> None:
        """Default fallback: inject empty context (no-op)."""
        pass


# ---------------------------------------------------------------------------
# Hook Implementations
# ---------------------------------------------------------------------------


class OnSessionStartHook(LifecycleHook):
    """Hook 1: Initialize context on session start.

    Runs an anatomy scan if configured, initializes token budget,
    and loads previous session memories.
    """

    name = "on_session_start"

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        if ctx.config.anatomy_enabled and ctx.config.auto_scan_on_start:
            await ctx.scan_project(mode=ScanMode.FULL)

        logger.info(
            "Session %s started (agent=%s)",
            ctx.session_id,
            ctx.agent_id,
        )


class BeforeAgentInvokeHook(LifecycleHook):
    """Hook 2: Inject context before agent invocation.

    Generates and injects the anatomy + bug + memory context into
    the agent's system prompt or user message.
    """

    name = "before_agent_invoke"
    fallback_enabled = True

    def __init__(self, max_context_tokens: int = 8000):
        self.max_context_tokens = max_context_tokens

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        context_str = ctx.generate_context(
            include_anatomy=True,
            include_bugs=True,
            include_memory=True,
        )

        if context_str:
            # Estimate tokens and truncate if needed
            estimated_tokens = ctx.estimator.count(context_str)
            if estimated_tokens > self.max_context_tokens:
                logger.warning(
                    "Context too large (%d tokens), truncating to %d",
                    estimated_tokens,
                    self.max_context_tokens,
                )
                # Actually truncate the context string
                if ctx.estimator._encoding is not None:
                    # Use tiktoken encoding for precise truncation
                    tokens = ctx.estimator._encoding.encode(context_str)
                    context_str = ctx.estimator._encoding.decode(
                        tokens[: self.max_context_tokens]
                    )
                    context_str += "\n... (context truncated)"
                else:
                    # Fallback: character-ratio based truncation
                    ratio = 3.75  # mixed content chars/token
                    max_chars = int(self.max_context_tokens * ratio)
                    context_str = context_str[:max_chars]
                    context_str += "\n... (context truncated)"

            # Append context to system prompt
            if hook_ctx.system_prompt:
                hook_ctx.system_prompt = f"{hook_ctx.system_prompt}\n\n{context_str}"
            else:
                hook_ctx.system_prompt = context_str

    async def _fallback(self, ctx, hook_ctx) -> None:
        """Fallback: inject empty context (keep original prompt)."""
        logger.info("Context injection failed, proceeding with original prompt")


class AfterAgentInvokeHook(LifecycleHook):
    """Hook 3: Extract learnings after agent response.

    Analyzes agent response for useful facts, updates cerebrum memory,
    and records any new learnings.
    """

    name = "after_agent_invoke"

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        # Record token usage
        if hook_ctx.input_tokens or hook_ctx.output_tokens:
            ctx.record_token_usage(
                input_tokens=hook_ctx.input_tokens,
                output_tokens=hook_ctx.output_tokens,
                model_name=hook_ctx.model_name,
            )
            ctx.check_budget()

        # Extract simple learnings from response (basic heuristic)
        if hook_ctx.agent_response and ctx.config.cerebrum_enabled:
            self._extract_learnings(ctx, hook_ctx.agent_response)

    def _extract_learnings(self, ctx: SessionContextManager, response: str) -> None:
        """Extract simple learnings from agent response."""
        # Look for patterns like "I learned that..." or "Note: ..."
        import re

        patterns = [
            re.compile(r"(?:I\s+(?:learned|discovered|found))\s+that\s+(.+?)[.!]", re.IGNORECASE),
            re.compile(r"(?:Note|Important|Key insight):\s*(.+?)[.!]", re.IGNORECASE),
            re.compile(r"(?:Remember|Memory):\s*(.+?)[.!]", re.IGNORECASE),
        ]

        for pattern in patterns:
            matches = pattern.findall(response)
            for i, match in enumerate(matches[:3]):  # Max 3 learnings per response
                ctx.remember(
                    key=f"learning_{ctx.session_id}_{i}",
                    value=match.strip(),
                    category="learning",
                    confidence=0.7,
                    ttl_seconds=86400,  # 24 hours
                )


class OnToolCallHook(LifecycleHook):
    """Hook 4: Before tool call — waste detection and file read tracking."""

    name = "on_tool_call"

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        if hook_ctx.tool_name in ("read_file", "read", "cat", "get_file"):
            file_path = hook_ctx.tool_input.get("file_path", "") if hook_ctx.tool_input else ""
            if file_path and ctx.is_wasteful_read(file_path):
                logger.warning(
                    "Wasteful read detected: '%s' (read %d times)",
                    file_path,
                    ctx.waste_detector.get_read_count(file_path),
                )


class OnToolResultHook(LifecycleHook):
    """Hook 5: After tool result — record output, detect duplicates."""

    name = "on_tool_result"

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        if hook_ctx.tool_name and hook_ctx.tool_output:
            # Record output for waste detection
            ctx.waste_detector.record_tool_output(
                hook_ctx.tool_name, hook_ctx.tool_output
            )

            # Track file reads
            if hook_ctx.tool_name in ("read_file", "read", "cat", "get_file"):
                file_path = hook_ctx.tool_input.get("file_path", "") if hook_ctx.tool_input else ""
                if file_path:
                    token_count = ctx.estimator.count(hook_ctx.tool_output)
                    ctx.record_file_read(file_path, token_count)


class OnErrorHook(LifecycleHook):
    """Hook 6: On error — log bug, update error memory."""

    name = "on_error"

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        if hook_ctx.error_type and hook_ctx.error_message:
            ctx.log_bug(
                error_type=hook_ctx.error_type,
                error_message=hook_ctx.error_message,
                error_traceback=hook_ctx.error_traceback,
                file_path=hook_ctx.metadata.get("file_path"),
                line_number=hook_ctx.metadata.get("line_number"),
            )

            # Remember error for future avoidance
            if ctx.config.cerebrum_enabled:
                ctx.remember(
                    key=f"error_{hook_ctx.error_type}",
                    value=f"Encountered {hook_ctx.error_type}: {hook_ctx.error_message[:200]}",
                    category="error",
                    confidence=0.9,
                    ttl_seconds=86400 * 7,  # 7 days
                )


class OnSessionEndHook(LifecycleHook):
    """Hook 7: On session end — persist state, generate summary."""

    name = "on_session_end"

    async def execute(self, ctx: SessionContextManager, hook_ctx: HookContext) -> None:
        summary = ctx.get_summary()

        logger.info(
            "Session %s ended — tokens: %d, bugs: %d, memories: %d",
            ctx.session_id,
            summary.get("tokens", {}).get("total_tokens", 0),
            summary.get("bugs", {}).get("total", 0),
            summary.get("memory", {}).get("total_memories", 0),
        )

        # Store summary as a memory
        if ctx.config.cerebrum_enabled:
            import json

            ctx.remember(
                key=f"session_summary_{ctx.session_id}",
                value=json.dumps(summary, default=str),
                category="session",
                confidence=1.0,
            )

        ctx.shutdown()


# ---------------------------------------------------------------------------
# Lifecycle Manager
# ---------------------------------------------------------------------------


class ContextLifecycle:
    """Manages all lifecycle hooks and orchestrates their execution.

    Usage:
        lifecycle = ContextLifecycle(session_ctx)
        lifecycle.register(OnSessionStartHook())
        lifecycle.register(BeforeAgentInvokeHook())
        ...
        await lifecycle.fire("on_session_start", hook_ctx)
    """

    def __init__(self, session_ctx: SessionContextManager):
        self.session_ctx = session_ctx
        self._hooks: dict[str, list[LifecycleHook]] = {}

    def register(self, hook: LifecycleHook) -> None:
        """Register a lifecycle hook."""
        if hook.name not in self._hooks:
            self._hooks[hook.name] = []
        self._hooks[hook.name].append(hook)

    def register_all(self, hooks: list[LifecycleHook]) -> None:
        """Register multiple hooks."""
        for hook in hooks:
            self.register(hook)

    def create_default_hooks(self) -> list[LifecycleHook]:
        """Create the default set of lifecycle hooks."""
        return [
            OnSessionStartHook(),
            BeforeAgentInvokeHook(),
            AfterAgentInvokeHook(),
            OnToolCallHook(),
            OnToolResultHook(),
            OnErrorHook(),
            OnSessionEndHook(),
        ]

    async def fire(self, hook_name: str, hook_ctx: HookContext) -> list[bool]:
        """Fire all hooks registered for a given lifecycle event.

        Returns a list of booleans indicating success/failure for each hook.
        """
        hooks = self._hooks.get(hook_name, [])
        results: list[bool] = []

        for hook in hooks:
            success = await hook.execute_safe(self.session_ctx, hook_ctx)
            results.append(success)

        return results

    async def fire_all(self, hook_ctx: HookContext) -> dict[str, list[bool]]:
        """Fire all registered hooks with the same context."""
        results: dict[str, list[bool]] = {}
        for hook_name in self._hooks:
            results[hook_name] = await self.fire(hook_name, hook_ctx)
        return results