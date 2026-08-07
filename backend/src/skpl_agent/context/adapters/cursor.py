"""
Cursor Adapter — Integrates SKPL context with Cursor IDE's AI agent.

Cursor uses .cursorrules and .cursor/rules/ for project configuration.
This adapter translates SKPL context into Cursor's rule format and
extracts learnings from Cursor's agent responses.

Reference: https://docs.cursor.com/context/rules-for-ai
"""

from __future__ import annotations

from typing import Any

from skpl_agent.context.adapters import AdapterContext, BaseAdapter


class CursorAdapter(BaseAdapter):
    """Adapter for Cursor IDE's AI agent."""

    agent_name = "cursor"

    def translate_context(self, ctx: AdapterContext) -> str:
        """Translate SKPL context into Cursor .cursorrules format."""
        sections: list[str] = []

        if ctx.anatomy:
            sections.append(
                "## Project Architecture\n"
                "The following describes the project's code structure:\n\n"
                f"{ctx.anatomy}"
            )

        if ctx.bugs:
            sections.append(
                "## Known Issues to Avoid\n"
                f"{ctx.bugs}"
            )

        if ctx.memory:
            sections.append(
                "## Project Knowledge\n"
                f"{ctx.memory}"
            )

        # Cursor-specific: always include a "You are" section
        header = (
            "You are an expert AI programming assistant integrated with SKPL Agent.\n"
            "You have access to the project's code structure, known issues, and\n"
            "learned context from previous sessions.\n"
        )

        return header + "\n" + "\n\n".join(sections)

    def extract_learnings(self, response: str) -> list[dict[str, Any]]:
        """Extract learnings from Cursor agent response."""
        learnings: list[dict[str, Any]] = []

        import re

        patterns = [
            re.compile(r"@cursorrule\s+(.+?)(?:\n|$)", re.IGNORECASE),
            re.compile(r"// @rule\s+(.+?)(?:\n|$)", re.IGNORECASE),
            re.compile(r"# @knowledge\s+(.+?)(?:\n|$)", re.IGNORECASE),
        ]

        for pattern in patterns:
            matches = pattern.findall(response)
            for match in matches:
                learnings.append({
                    "value": match.strip(),
                    "confidence": 0.7,
                    "source": "cursor",
                })

        return learnings

    def get_system_prompt_extension(self) -> str:
        return """
Additional context from SKPL Agent has been loaded. You can use the
provided project structure, known issues, and session memory to make
more informed decisions about the codebase.
"""

    def get_tool_definitions(self) -> list[dict]:
        return []  # Cursor uses its own tool system

    def export_cursorrules(self, ctx: AdapterContext) -> str:
        """Export context in .cursorrules format."""
        rules = ["# SKPL Agent Context Rules (auto-generated)", ""]

        if ctx.anatomy:
            rules.append("## Project Structure")
            rules.append(ctx.anatomy)
            rules.append("")

        if ctx.bugs:
            rules.append("## Known Issues")
            rules.append(ctx.bugs)
            rules.append("")

        if ctx.memory:
            rules.append("## Learned Context")
            rules.append(ctx.memory)
            rules.append("")

        return "\n".join(rules)