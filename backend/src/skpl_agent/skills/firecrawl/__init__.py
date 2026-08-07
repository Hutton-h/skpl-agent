"""Firecrawl Skill — web scraping and content extraction plugin.

This skill integrates Firecrawl's web scraping capabilities into the
SKPL Agent platform as a modular, loadable plugin via the skill registry.

Provides:
- Single-page scraping with content extraction
- Recursive website crawling with depth control
- Web search integration
- Site map generation
- Structured data extraction with LLM
- Content parsing and formatting
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Skill Metadata
# ---------------------------------------------------------------------------


@dataclass
class FirecrawlSkillMetadata:
    """Metadata for the Firecrawl skill."""

    name: str = "firecrawl"
    display_name: str = "Firecrawl"
    version: str = "1.0.0"
    description: str = "Web scraping, crawling, and content extraction using Firecrawl API"
    author: str = "SKPL Agent Contributors"
    homepage: str = "https://github.com/mendableai/firecrawl"
    license: str = "AGPL-3.0"
    requires: list[str] = field(default_factory=lambda: ["skpl-agent[web]"])
    provides: list[str] = field(default_factory=lambda: [
        "web.scrape", "web.crawl", "web.search", "web.map", "web.extract", "web.parse",
    ])
    mcp_config: str = "skills/firecrawl/mcp_config.json"
    tags: list[str] = field(default_factory=lambda: [
        "web", "scraping", "crawling", "search", "content-extraction",
    ])


FIRECRAWL_SKILL_METADATA = FirecrawlSkillMetadata()


# ---------------------------------------------------------------------------
# Skill Implementation
# ---------------------------------------------------------------------------


class FirecrawlSkill:
    """Firecrawl web scraping skill.

    Provides a unified interface to all Firecrawl API operations through
    the skill system. Each tool is exposed as an async method that can be
    called by agent frameworks.
    """

    def __init__(self) -> None:
        self._metadata = FIRECRAWL_SKILL_METADATA
        self._client = None
        self._initialized = False

    @property
    def metadata(self) -> FirecrawlSkillMetadata:
        return self._metadata

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the Firecrawl client with API key and endpoint."""
        from skpl_agent.skills.firecrawl.firecrawl_client import FirecrawlClient

        settings = config or {}
        api_key = settings.get("api_key") or settings.get("FIRECRAWL_API_KEY", "")
        endpoint = settings.get("endpoint") or settings.get("FIRECRAWL_API_ENDPOINT", "https://api.firecrawl.dev")

        self._client = FirecrawlClient(
            api_key=api_key,
            base_url=endpoint,
        )
        self._initialized = True

    async def shutdown(self) -> None:
        """Clean up Firecrawl resources."""
        if self._client:
            await self._client.close()
        self._initialized = False

    async def scrape(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Scrape a single URL and extract its content."""
        self._ensure_initialized()
        return await self._client.scrape(url, **kwargs)

    async def crawl(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Crawl a website recursively."""
        self._ensure_initialized()
        return await self._client.crawl(url, **kwargs)

    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search the web using Firecrawl."""
        self._ensure_initialized()
        return await self._client.search(query, **kwargs)

    async def map(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Discover all URLs on a site."""
        self._ensure_initialized()
        return await self._client.map(url, **kwargs)

    async def extract(self, urls: list[str], prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Extract structured data from URLs using LLM."""
        self._ensure_initialized()
        return await self._client.extract(urls, prompt, **kwargs)

    async def parse(self, content: str, **kwargs: Any) -> dict[str, Any]:
        """Parse raw content into structured format."""
        self._ensure_initialized()
        return await self._client.parse(content, **kwargs)

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError("FirecrawlSkill not initialized. Call initialize() first.")


__all__ = [
    "FirecrawlSkill",
    "FIRECRAWL_SKILL_METADATA",
    "FirecrawlSkillMetadata",
]