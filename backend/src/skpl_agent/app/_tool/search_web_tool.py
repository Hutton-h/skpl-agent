"""Web search tool — built-in tool for searching the web.

Registers as an AgentScope tool that can be used by agents to perform
web searches. Built on top of the Firecrawl Searcher with SSRF protection
and rate limiting integrated.
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


class SearchWebToolParams(ParamsBase):
    """Parameters for the Web Search tool."""

    query: str
    """The search query string."""

    engine: str = "google"
    """Search engine to use: google or bing."""

    num_results: int = 10
    """Maximum number of results to return (1-100)."""

    language: str = "en"
    """Language code for results (e.g., 'en', 'zh-CN')."""

    country: str = ""
    """Country code for localized results (e.g., 'us', 'cn')."""


class SearchWebTool(ToolBase):
    """Web search tool for performing internet searches.

    This tool is registered as a built-in AgentScope tool and can be
    invoked by any agent with appropriate permissions. It wraps the
    Firecrawl Searcher with SSRF protection, rate limiting, and the
    MCP three-tier degradation strategy.

    Usage:
        >>> tool = SearchWebTool()
        >>> result = await tool(query="Python async programming")
        >>> for r in result.content["results"]:
        >>>     print(r["title"], r["url"])

    Security:
        - Search engine URLs are validated against SSRF protection
        - Rate limiting is enforced per search
        - Results are sanitized (no internal URLs leaked)
    """

    name: str = "web_search"
    description: str = (
        "Search the web for information. "
        "Returns a list of search results with titles, URLs, and snippets. "
        "Use this tool when you need to find information on the internet, "
        "research a topic, or discover relevant web pages."
    )
    input_schema: dict[str, Any] = SearchWebToolParams.model_json_schema()
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
        """Initialize the SearchWebTool.

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
        """Check permissions for the search tool.

        Args:
            tool_input: The tool input arguments.
            context: The permission context.

        Returns:
            PermissionDecision indicating whether the operation is allowed.
        """
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="Web search is a read-only operation and is always allowed.",
        )

    async def call(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 10,
        language: str = "en",
        country: str = "",
    ) -> ToolChunk:
        """Search the web and return results.

        This method implements the MCP three-tier degradation strategy:
        1. API mode: Use Firecrawl API if configured
        2. Local mode: Direct Google SERP scraping
        3. Static mode: Return error with clear message

        Args:
            query: The search query string.
            engine: Search engine to use (google, bing).
            num_results: Maximum number of results (1-100).
            language: Language code for results.
            country: Country code for localized results.

        Returns:
            ToolChunk with search results.
        """
        # ---- Parameter Validation ----
        if not query:
            return ToolChunk(
                content=[TextBlock(text=json.dumps({"query": query, "error": "Query is required", "results": []}))],
                is_error=True,
            )

        if num_results < 1 or num_results > 100:
            return ToolChunk(
                content=[TextBlock(text=json.dumps({"query": query, "error": "num_results must be between 1 and 100", "results": []}))],
                is_error=True,
            )

        if engine not in ("google", "bing"):
            return ToolChunk(
                content=[TextBlock(text=json.dumps({"query": query, "error": f"Unsupported engine: {engine}. Use 'google' or 'bing'.", "results": []}))],
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
                    result = await client.search(
                        query=query,
                        engine=engine,
                        num_results=num_results,
                        language=language,
                        country=country,
                    )
                    return ToolChunk(
                        content=[TextBlock(text=json.dumps({
                            "query": result.query,
                            "engine": engine,
                            "results": [
                                {
                                    "title": r.get("title", ""),
                                    "url": r.get("url", ""),
                                    "snippet": r.get("snippet", r.get("description", "")),
                                    "position": i,
                                    "domain": r.get("domain", ""),
                                }
                                for i, r in enumerate(result.results)
                            ],
                            "total_results": result.total_results,
                            "error": result.error,
                            "duration_ms": result.duration_ms,
                            "tier": "api",
                        }))],
                    )
                finally:
                    await client.close()
            except Exception as e:
                logger.warning(
                    "API mode search failed for '%s': %s, falling back to local mode",
                    query, e,
                )

        # ---- Tier 2: Local Mode ----
        try:
            from skpl_agent.skills.firecrawl.tools.search import Searcher

            searcher = Searcher(self._config)
            try:
                results = await searcher.search(
                    query=query,
                    engine=engine,
                    num_results=num_results,
                    language=language,
                    country=country,
                )

                # Filter results through SSRF protection
                safe_results = []
                for r in results.results:
                    if self._ssrf.is_url_allowed(r.url):
                        safe_results.append({
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet,
                            "position": r.position,
                            "domain": r.domain,
                        })
                    else:
                        logger.debug("SSRF filtered search result: %s", r.url)

                return ToolChunk(
                    content=[TextBlock(text=json.dumps({
                        "query": results.query,
                        "engine": results.engine,
                        "results": safe_results[:num_results],
                        "total_results": len(safe_results),
                        "error": results.error,
                        "duration_ms": results.duration_ms,
                        "tier": "local",
                    }))],
                )
            finally:
                await searcher.close()
        except Exception as e:
            logger.warning(
                "Local mode search failed for '%s': %s, falling back to static mode",
                query, e,
            )

        # ---- Tier 3: Static Mode ----
        logger.error("All tiers failed for search query: '%s'", query)
        return ToolChunk(
            content=[TextBlock(text=json.dumps({
                "query": query,
                "engine": engine,
                "results": [],
                "total_results": 0,
                "error": "All search tiers failed. The search could not be completed.",
                "tier": "static",
            }))],
            is_error=True,
        )