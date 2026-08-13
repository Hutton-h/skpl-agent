"""Web scrape tool — built-in tool for scraping a single URL.

Registers as an AgentScope tool that can be used by agents to fetch
and extract content from web pages. Built on top of the Firecrawl
Scraper with SSRF protection and rate limiting integrated.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from skpl_agent.tool._base import ToolBase, ParamsBase
from skpl_agent.tool._response import ToolChunk
from skpl_agent.message import TextBlock
from skpl_agent.permission import PermissionContext, PermissionDecision, PermissionBehavior
from skpl_agent.app._security.ssrf import SSRFProtection, SSRFError
from skpl_agent.app._service.firecrawl_service import FirecrawlConfig

logger = logging.getLogger(__name__)


class ScrapeToolParams(ParamsBase):
    """Parameters for the Web Scrape tool."""

    url: str
    """The URL to scrape. Must be a valid HTTP/HTTPS URL."""

    formats: list[str] = ["markdown"]
    """Output formats to include: markdown, html, text."""

    only_main_content: bool = True
    """Extract only the main content, excluding boilerplate."""

    wait_for: int = 0
    """Wait time in milliseconds before scraping (for JS-rendered pages)."""


class ScrapeTool(ToolBase):
    """Web scraping tool for fetching and extracting web page content.

    This tool is registered as a built-in AgentScope tool and can be
    invoked by any agent with appropriate permissions. It wraps the
    Firecrawl Scraper with SSRF protection, rate limiting, and the
    MCP three-tier degradation strategy.

    Usage:
        >>> tool = ScrapeTool()
        >>> result = await tool(url="https://example.com")
        >>> print(result.content)

    Security:
        - All URLs are validated against SSRF protection rules
        - Rate limiting is enforced per domain
        - Internal/private network URLs are blocked
    """

    name: str = "web_scrape"
    description: str = (
        "Scrape a single web page and extract its content. "
        "Returns the page title, description, content in markdown/HTML/text, "
        "discovered links, images, and metadata. "
        "Use this tool when you need to read the content of a specific web page."
    )
    input_schema: dict[str, Any] = ScrapeToolParams.model_json_schema()
    is_concurrency_safe: bool = True
    is_read_only: bool = True
    is_external_tool: bool = False
    is_state_injected: bool = False
    is_mcp: bool = False

    def __init__(
        self,
        config: FirecrawlConfig | None = None,
        middlewares: list | None = None,
    ) -> None:
        """Initialize the ScrapeTool.

        Args:
            config: Firecrawl configuration. If None, defaults are used.
            middlewares: Optional list of tool middlewares.
        """
        super().__init__(middlewares=middlewares)
        self._config = config or FirecrawlConfig()
        self._ssrf = SSRFProtection(
            block_localhost=True,
            dns_rebinding_protection=True,
        )

    async def check_permissions(
        self,
        tool_input: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionDecision:
        """Check permissions for the scrape tool.

        Args:
            tool_input: The tool input arguments.
            context: The permission context.

        Returns:
            PermissionDecision indicating whether the operation is allowed.
        """
        # Always allow read-only web scraping
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="Web scraping is a read-only operation and is always allowed.",
        )

    async def call(
        self,
        url: str,
        formats: list[str] | None = None,
        only_main_content: bool = True,
        wait_for: int = 0,
    ) -> ToolChunk:
        """Scrape a web page and extract content.

        This method implements the MCP three-tier degradation strategy:
        1. API mode: Use Firecrawl API if configured
        2. Local mode: Direct HTTP scraping with BeautifulSoup
        3. Static mode: Return error with clear message

        Args:
            url: The URL to scrape.
            formats: Output formats (markdown, html, text).
            only_main_content: Extract only main content.
            wait_for: Wait time in ms for JS rendering.

        Returns:
            ToolChunk with the scraped content.
        """
        formats = formats or ["markdown"]

        # ---- SSRF Validation ----
        try:
            self._ssrf.validate_url(url)
        except SSRFError as e:
            logger.warning("SSRF blocked URL: %s — %s", url, e)
            return ToolChunk(
                content=[TextBlock(text=json.dumps({
                    "url": url,
                    "error": f"SSRF protection blocked this URL: {e}",
                    "title": "",
                    "content_markdown": "",
                    "status_code": 0,
                }))],
                is_error=True,
            )

        # ---- Parameter Validation ----
        if not url:
            return ToolChunk(
                content=[TextBlock(text=json.dumps({"url": url, "error": "URL is required"}))],
                is_error=True,
            )

        if wait_for < 0 or wait_for > 30000:
            return ToolChunk(
                content=[TextBlock(text=json.dumps({"url": url, "error": "wait_for must be between 0 and 30000 ms"}))],
                is_error=True,
            )

        # ---- Tier 1: API Mode ----
        if self._config.api_key:
            try:
                from skpl_agent.skills.firecrawl.firecrawl_client import FirecrawlClient

                client = FirecrawlClient(
                    api_key=self._config.api_key,
                    api_endpoint=self._config.api_endpoint,
                    timeout=self._config.timeout_seconds,
                )
                try:
                    result = await client.scrape(
                        url=url,
                        formats=formats,
                        only_main_content=only_main_content,
                        wait_for=wait_for,
                    )
                    return ToolChunk(
                        content=[TextBlock(text=json.dumps({
                            "url": result.url,
                            "title": result.title,
                            "description": result.description,
                            "content_markdown": result.markdown,
                            "content_html": result.html,
                            "content_text": result.text,
                            "links": result.links,
                            "images": result.images,
                            "metadata": result.metadata,
                            "status_code": result.status_code,
                            "error": result.error,
                            "duration_ms": result.duration_ms,
                            "tier": "api",
                        }))],
                    )
                finally:
                    await client.close()
            except Exception as e:
                logger.warning(
                    "API mode scrape failed for %s: %s, falling back to local mode",
                    url, e,
                )

        # ---- Tier 2: Local Mode ----
        try:
            from skpl_agent.skills.firecrawl.tools.scrape import Scraper

            scraper = Scraper(self._config)
            try:
                result = await scraper.scrape(url)
                return ToolChunk(
                    content=[TextBlock(text=json.dumps({
                        "url": result.url,
                        "title": result.title,
                        "description": result.description,
                        "content_markdown": result.content_markdown,
                        "content_html": result.content_html,
                        "content_text": result.content_text,
                        "links": result.links,
                        "images": result.images,
                        "metadata": result.metadata,
                        "status_code": result.status_code,
                        "error": result.error,
                        "duration_ms": result.duration_ms,
                        "tier": "local",
                    }))],
                )
            finally:
                await scraper.close()
        except Exception as e:
            logger.warning(
                "Local mode scrape failed for %s: %s, falling back to static mode",
                url, e,
            )

        # ---- Tier 3: Static Mode ----
        logger.error("All tiers failed for URL: %s", url)
        return ToolChunk(
            content=[TextBlock(text=json.dumps({
                "url": url,
                "error": "All scraping tiers failed. The URL could not be reached.",
                "title": "",
                "content_markdown": "",
                "status_code": 0,
                "tier": "static",
            }))],
            is_error=True,
        )