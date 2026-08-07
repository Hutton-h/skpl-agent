"""Base adapter interface for external agent tools.

External agent adapters (Claude Code, Codex, Cursor) implement this
interface to provide context injection and lifecycle hooks for
third-party coding agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterContext:
    """Context passed to an external agent adapter."""

    session_id: str
    working_directory: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    """Result returned from an external agent adapter."""

    success: bool
    output: str = ""
    tokens_used: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """Abstract base class for external agent adapters.

    Implementations provide context injection and command execution
    bridges to third-party coding agents like Claude Code, Codex, and
    Cursor.
    """

    name: str = "base"
    version: str = "0.1.0"

    @abstractmethod
    async def inject_context(self, ctx: AdapterContext, content: str) -> bool:
        """Inject context content into the external agent session.

        Args:
            ctx: The adapter context (session, working directory, etc.)
            content: The context content to inject (e.g. anatomy data,
                     token usage, bug reports).

        Returns:
            True if injection succeeded, False otherwise.
        """
        ...

    @abstractmethod
    async def extract_context(self, ctx: AdapterContext) -> dict[str, Any]:
        """Extract context from the external agent session.

        Args:
            ctx: The adapter context.

        Returns:
            A dictionary of extracted context data.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the external agent tool is available on the system.

        Returns:
            True if the tool binary/CLI is found and accessible.
        """
        ...

    async def on_session_start(self, ctx: AdapterContext) -> None:
        """Hook called when a session starts. Override in subclasses."""
        pass

    async def on_session_end(self, ctx: AdapterContext) -> None:
        """Hook called when a session ends. Override in subclasses."""
        pass

    async def health_check(self) -> dict[str, Any]:
        """Run a health check on the adapter.

        Returns:
            A dict with ``status`` (ok/error) and optional ``message``.
        """
        try:
            available = await self.is_available()
            return {
                "status": "ok" if available else "error",
                "available": available,
                "name": self.name,
                "version": self.version,
            }
        except Exception as exc:
            return {
                "status": "error",
                "available": False,
                "name": self.name,
                "version": self.version,
                "message": str(exc),
            }