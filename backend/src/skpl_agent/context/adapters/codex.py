"""
OpenAI Codex / ChatGPT Adapter — Integrates SKPL context with OpenAI agents.

Supports both the Codex CLI and ChatGPT-based agents, translating
SKPL context into the format expected by OpenAI's tool-calling
and system prompt conventions.

Reference: https://platform.openai.com/docs/guides/agents
"""

from __future__ import annotations

from typing import Any

from skpl_agent.context.adapters import AdapterContext, BaseAdapter


class CodexAdapter(BaseAdapter):
    """Adapter for OpenAI Codex CLI and ChatGPT agents."""

    agent_name = "codex"

    def translate_context(self, ctx: AdapterContext) -> str:
        """Translate SKPL context into OpenAI agent format."""
        sections: list[str] = []

        if ctx.anatomy:
            sections.append(
                "## Project Context\n"
                "The following is the project's code structure and symbols:\n\n"
                f"{ctx.anatomy}"
            )

        if ctx.bugs:
            sections.append(
                "## Recent Issues\n"
                "Be aware of these recently encountered issues:\n\n"
                f"{ctx.bugs}"
            )

        if ctx.memory:
            sections.append(
                "## Session Memory\n"
                "Relevant context from previous interactions:\n\n"
                f"{ctx.memory}"
            )

        if ctx.token_summary:
            sections.append(
                f"## Token Budget\n"
                f"Used: {ctx.token_summary.get('total_tokens', 0)} tokens\n"
                f"Budget: {ctx.token_summary.get('token_budget', 'unlimited')}"
            )

        return "\n\n".join(sections)

    def extract_learnings(self, response: str) -> list[dict[str, Any]]:
        """Extract learnings from Codex response."""
        learnings: list[dict[str, Any]] = []

        import re

        patterns = [
            re.compile(r"memory:\s*(.+?)(?:\n|$)", re.IGNORECASE),
            re.compile(r"REMEMBER:\s*(.+?)(?:\n|$)", re.IGNORECASE),
            re.compile(r"// @memory\s+(.+?)(?:\n|$)", re.IGNORECASE),
        ]

        for pattern in patterns:
            matches = pattern.findall(response)
            for match in matches:
                learnings.append({
                    "value": match.strip(),
                    "confidence": 0.7,
                    "source": "codex",
                })

        return learnings

    def get_system_prompt_extension(self) -> str:
        return """
You are integrated with SKPL Agent's context management system.
The project context, known issues, and session memory have been
provided above. Use the `skpl_remember` function to store important
learnings for future sessions.
"""

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "skpl_remember",
                    "description": "Store a key learning in SKPL Agent's memory system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "A unique key for this memory",
                            },
                            "value": {
                                "type": "string",
                                "description": "The learning to remember",
                            },
                            "category": {
                                "type": "string",
                                "enum": ["general", "preference", "error", "pattern", "fact"],
                                "description": "Category of the memory",
                            },
                        },
                        "required": ["key", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "skpl_search_symbols",
                    "description": "Search the project's code structure for symbols",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for symbol names",
                            },
                            "language": {
                                "type": "string",
                                "description": "Filter by programming language",
                            },
                            "kind": {
                                "type": "string",
                                "enum": ["function", "class", "method", "variable", "interface", "type", "enum", "module"],
                                "description": "Filter by symbol type",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
        ]