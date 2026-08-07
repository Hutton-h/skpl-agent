"""
External Agent Adapters — Integrate SKPL context with external agents.

Provides adapters for Claude Code, Codex, Cursor, and other external
agents, allowing them to consume SKPL context management (anatomy,
bugs, memories) alongside AgentScope's internal agents.

Architecture:
    External Agent → Adapter.translate() → SKPL Context
    SKPL Context → Adapter.export() → External Agent format

Each adapter handles the specific prompt format and tool integrations
of its target agent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Adapter Protocol
# ---------------------------------------------------------------------------


@dataclass
class AdapterContext:
    """Context data passed to/from adapters."""

    anatomy: str = ""
    bugs: str = ""
    memory: str = ""
    token_summary: dict = field(default_factory=dict)
    raw_context: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """Base class for external agent adapters.

    Each adapter translates between SKPL's internal context format
    and the target agent's expected prompt format.
    """

    agent_name: str = "base"

    @abstractmethod
    def translate_context(self, ctx: AdapterContext) -> str:
        """Translate SKPL context into agent-specific prompt format."""
        ...

    @abstractmethod
    def extract_learnings(self, response: str) -> list[dict[str, Any]]:
        """Extract learnings from agent response."""
        ...

    def get_system_prompt_extension(self) -> str:
        """Get agent-specific system prompt additions."""
        return ""

    def get_tool_definitions(self) -> list[dict]:
        """Get agent-specific tool definitions."""
        return []

    def can_handle(self, agent_type: str) -> bool:
        """Check if this adapter can handle the given agent type."""
        return agent_type.lower() == self.agent_name.lower()