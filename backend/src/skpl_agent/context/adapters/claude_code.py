"""
Claude Code Adapter — Integrates SKPL context with Claude Code (CLI).

Claude Code uses a specific CLAUDE.md format for project context.
This adapter translates SKPL anatomy, bugs, and memories into
Claude Code's expected format.

Reference: https://docs.anthropic.com/en/docs/claude-code
"""

from __future__ import annotations

from typing import Any

from skpl_agent.context.adapters import AdapterContext, BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    """Adapter for Claude Code (Anthropic's CLI agent)."""

    agent_name = "claude_code"

    def translate_context(self, ctx: AdapterContext) -> str:
        """Translate SKPL context into CLAUDE.md format."""
        sections: list[str] = []

        if ctx.anatomy:
            sections.append(f"## Project Structure\n\n{ctx.anatomy}")

        if ctx.bugs:
            sections.append(f"## Known Issues\n\n{ctx.bugs}")

        if ctx.memory:
            sections.append(f"## Context & Learnings\n\n{ctx.memory}")

        return "\n\n".join(sections)

    def extract_learnings(self, response: str) -> list[dict[str, Any]]:
        """Extract learnings from Claude Code response."""
        learnings: list[dict[str, Any]] = []

        # Claude Code uses specific markers for learnings
        import re

        patterns = [
            re.compile(r"/remember\s+(.+?)(?:\n|$)", re.IGNORECASE),
            re.compile(r"CLAUDE\.MD\s+update:\s*(.+?)(?:\n|$)", re.IGNORECASE),
            re.compile(r"(?:Key\s+)?(?:Finding|Insight|Learning):\s*(.+?)(?:\n|$)", re.IGNORECASE),
        ]

        for pattern in patterns:
            matches = pattern.findall(response)
            for match in matches:
                learnings.append({
                    "value": match.strip(),
                    "confidence": 0.7,
                    "source": "claude_code",
                })

        return learnings

    def get_system_prompt_extension(self) -> str:
        return """
You have access to SKPL Agent's context management system. The project
anatomy, known bugs, and learned memories have been provided above.
Use this context to make more informed decisions.
"""

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "skpl_remember",
                "description": "Store a learning in SKPL's memory system for future sessions",
                "parameters": {
                    "key": {"type": "string", "description": "Memory key"},
                    "value": {"type": "string", "description": "Memory value"},
                    "category": {"type": "string", "description": "Memory category"},
                },
            },
            {
                "name": "skpl_search",
                "description": "Search SKPL's anatomy index for symbols",
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "language": {"type": "string", "description": "Filter by language"},
                },
            },
        ]