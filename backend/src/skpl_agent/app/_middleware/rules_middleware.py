"""Rules middleware — enforces behavioral constraints on agent responses.

Based on Superpowers' "Red Flags" system, this middleware injects
behavioral rules into the agent's system prompt and optionally validates
responses against those rules. It is the SKPL equivalent of constraint-
based prompting — ensuring the agent follows project conventions without
requiring the user to repeat them in every conversation.

Architecture:
    - ``on_system_prompt``: appends a curated rules block to the system
      prompt, covering code quality, security, and communication norms.
    - ``on_reply``: (future) validates the agent's response against
      red-flag patterns and can inject warnings or corrections.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Callable, TYPE_CHECKING

from skpl_agent.middleware._base import MiddlewareBase

if TYPE_CHECKING:
    from skpl_agent.agent import Agent

logger = logging.getLogger(__name__)

# ── Default rule sets ──────────────────────────────────────────────────────
# These are the built-in behavioral constraints. They can be overridden
# per-agent or per-session via the Cerebrum service.

DEFAULT_CODING_RULES = """
## Coding Rules (CRITICAL — must follow)
- ALWAYS read existing code before editing — never guess the current state
- Use the project's existing conventions (indentation, naming, imports)
- ONE logical change per edit — never batch unrelated changes
- Include error handling for all I/O, network, and file operations
- NEVER hardcode secrets, API keys, or passwords
- Prefer standard library over external dependencies unless justified
- When generating code, include type hints (Python) or JSDoc (TypeScript)
- Delete dead code — don't comment it out
- Verify imports are correct before writing files
"""

DEFAULT_SECURITY_RULES = """
## Security Rules (CRITICAL — must follow)
- NEVER execute arbitrary code from untrusted sources
- NEVER expose credentials, tokens, or API keys in responses
- When handling user data, assume it's untrusted — sanitize inputs
- NEVER suggest or use `eval()`, `exec()`, or `os.system()` with user input
- When generating SQL, use parameterized queries — never string concatenation
- NEVER disable SSL verification or security warnings
- When generating HTML, escape user input to prevent XSS
- Report security issues immediately — don't try to fix them silently
"""

DEFAULT_COMMUNICATION_RULES = """
## Communication Rules
- Be concise — prefer short answers with code over long explanations
- When the user asks for a file, CREATE it — don't just show the content
- When the user reports an error, investigate the ROOT CAUSE — not the symptom
- If you don't know something, say so — don't fabricate information
- When making assumptions, state them explicitly
- Structure complex answers with headers and code blocks
- Prefer showing over telling — use code examples, diagrams, and tables
"""

DEFAULT_TOOL_RULES = """
## Tool Usage Rules
- Read files BEFORE editing them — never edit blind
- Use Grep/Glob for searching — not shell commands
- Use the Write tool for creating files — not shell redirection
- When generating files, write to the appropriate workspace directory
- Use publish_visual for charts, tables, and comparisons — not plain text
- When the user asks for a document, use docwriter skill for format selection
- Use RunPython for data processing, calculations, and file generation
- Batch independent operations — use parallel tool calls when possible
"""


def build_rules_block(
    *,
    coding: bool = True,
    security: bool = True,
    communication: bool = True,
    tools: bool = True,
    extra_rules: str | None = None,
) -> str:
    """Build a rules block string from the selected rule sets.

    Args:
        coding: Include coding rules.
        security: Include security rules.
        communication: Include communication rules.
        tools: Include tool usage rules.
        extra_rules: Additional custom rules to append.

    Returns:
        A formatted rules block string suitable for appending to the
        system prompt.
    """
    blocks: list[str] = []
    if coding:
        blocks.append(DEFAULT_CODING_RULES.strip())
    if security:
        blocks.append(DEFAULT_SECURITY_RULES.strip())
    if communication:
        blocks.append(DEFAULT_COMMUNICATION_RULES.strip())
    if tools:
        blocks.append(DEFAULT_TOOL_RULES.strip())
    if extra_rules:
        blocks.append(extra_rules.strip())

    if not blocks:
        return ""

    return "\n\n" + "\n\n".join(blocks)


class RulesMiddleware(MiddlewareBase):
    """Middleware that injects behavioral rules into the agent's system prompt.

    This is a non-invasive middleware — it only modifies the system prompt
    and does not intercept other hooks. Multiple instances can be stacked
    with different rule configurations.

    Usage:
        ```python
        agent = Agent(
            ...
            middlewares=[
                RulesMiddleware(coding=True, security=True),
            ],
        )
        ```

    To customize rules per session, use the Cerebrum service to store
    session-specific rules and retrieve them in the middleware factory:

        ```python
        async def rules_factory(user_id, agent_id, session_id):
            cerebrum = app.state.cerebrum_service
            extra = await cerebrum.get(f"rules:{session_id}")
            return [RulesMiddleware(extra_rules=extra)]
        ```
    """

    def __init__(
        self,
        *,
        coding: bool = True,
        security: bool = True,
        communication: bool = True,
        tools: bool = True,
        extra_rules: str | None = None,
    ) -> None:
        """Initialize the rules middleware.

        Args:
            coding: Include coding rules (default True).
            security: Include security rules (default True).
            communication: Include communication rules (default True).
            tools: Include tool usage rules (default True).
            extra_rules: Additional custom rules to append.
        """
        super().__init__()
        self._rules_block = build_rules_block(
            coding=coding,
            security=security,
            communication=communication,
            tools=tools,
            extra_rules=extra_rules,
        )

    async def on_system_prompt(
        self, agent: "Agent", current_prompt: str
    ) -> str:
        """Append behavioral rules to the system prompt.

        Args:
            agent: The Agent instance.
            current_prompt: The current system prompt string.

        Returns:
            The system prompt with rules appended.
        """
        if not self._rules_block:
            return current_prompt

        # Avoid duplicating rules if they're already in the prompt
        if self._rules_block.strip() in current_prompt:
            return current_prompt

        return current_prompt + self._rules_block

    async def get_middleware_key(self) -> str:
        """Unique key for state storage."""
        return "rules_middleware"


class SkillRoutingMiddleware(MiddlewareBase):
    """Middleware that injects skill routing guidance into the system prompt.

    Based on Superpowers' skill routing system, this middleware reads the
    available skills from the workspace and appends guidance on when to
    use each skill. This allows the main agent to automatically delegate
    to the appropriate skill without explicit user instruction.

    The skill list is refreshed on each agent assembly so that newly
    installed skills are immediately available.
    """

    def __init__(self, skill_descriptions: list[dict] | None = None) -> None:
        """Initialize the skill routing middleware.

        Args:
            skill_descriptions: Optional list of skill dicts with
                ``name``, ``description``, and ``when_to_use`` fields.
                If not provided, the middleware will be a no-op until
                skills are set via ``set_skills()``.
        """
        super().__init__()
        self._skills: list[dict] = skill_descriptions or []

    def set_skills(self, skills: list[dict]) -> None:
        """Update the skill list for the next agent assembly.

        Args:
            skills: List of skill dicts with name, description, when_to_use.
        """
        self._skills = skills

    def _build_skill_guidance(self) -> str:
        """Build the skill routing guidance block."""
        if not self._skills:
            return ""

        lines = [
            "\n\n## Available Skills",
            "You have access to specialized skills. When a user request matches",
            "a skill's trigger condition, invoke the skill by following its",
            "SKILL.md workflow. The skill list below shows when to use each one:",
            "",
        ]

        # Group by category
        by_category: dict[str, list[dict]] = {}
        for skill in self._skills:
            cat = skill.get("category", "general")
            by_category.setdefault(cat, []).append(skill)

        for cat, skills in sorted(by_category.items()):
            lines.append(f"### {cat.title()}")
            for skill in skills:
                name = skill.get("name", "unknown")
                desc = skill.get("description", "")
                when = skill.get("when_to_use", "")
                lines.append(f"- **{name}**: {desc}")
                if when:
                    lines.append(f"  Trigger: {when}")
            lines.append("")

        return "\n".join(lines)

    async def on_system_prompt(
        self, agent: "Agent", current_prompt: str
    ) -> str:
        """Append skill routing guidance to the system prompt.

        Args:
            agent: The Agent instance.
            current_prompt: The current system prompt string.

        Returns:
            The system prompt with skill routing guidance appended.
        """
        guidance = self._build_skill_guidance()
        if not guidance:
            return current_prompt

        if guidance.strip() in current_prompt:
            return current_prompt

        return current_prompt + guidance

    async def get_middleware_key(self) -> str:
        return "skill_routing_middleware"