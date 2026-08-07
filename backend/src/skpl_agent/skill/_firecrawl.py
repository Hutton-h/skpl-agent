"""Firecrawl skill loader — registers Firecrawl tools into the Skill system.

Provides FirecrawlSkill that discovers and registers all Firecrawl tools
(scrape, crawl, search, map, extract, parse) as MCP-compatible tools
within the AgentScope tool framework.

Architecture:
    FirecrawlSkill
        -> FirecrawlClient (API mode, when API key is configured)
        -> Scraper/Crawler/Searcher/... (local mode, when no API key)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from skpl_agent.skill import Skill
from skpl_agent.app._service.firecrawl_service import FirecrawlConfig

logger = logging.getLogger(__name__)

# Path to the skills directory relative to the project root
_SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "skills",
    "firecrawl",
)


class FirecrawlSkill:
    """Firecrawl skill loader and configuration manager.

    Discovers the Firecrawl skill from the skills directory, reads its
    SKILL.md metadata, and registers all Firecrawl tools (scrape, crawl,
    search, map, extract, parse) into the AgentScope tool system.

    Usage:
        >>> skill = FirecrawlSkill()
        >>> await skill.load()
        >>> tools = skill.get_tools()
        >>> for tool in tools:
        >>>     print(tool.name, tool.description)
    """

    def __init__(self, config: FirecrawlConfig | None = None) -> None:
        """Initialize the Firecrawl skill.

        Args:
            config: Firecrawl configuration. If None, defaults are used.
        """
        self._config = config or FirecrawlConfig()
        self._skill_metadata: Skill | None = None
        self._tools: dict[str, Any] = {}
        self._loaded = False

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        """The skill name."""
        return "firecrawl"

    @property
    def description(self) -> str:
        """The skill description."""
        if self._skill_metadata:
            return self._skill_metadata.description
        return "Web scraping, crawling, search, and extraction skill"

    @property
    def config(self) -> FirecrawlConfig:
        """The current Firecrawl configuration."""
        return self._config

    @property
    def is_loaded(self) -> bool:
        """Whether the skill has been loaded."""
        return self._loaded

    # ── Loading ──────────────────────────────────────────────────────────

    async def load(self) -> None:
        """Load the Firecrawl skill and register all tools.

        This method:
        1. Reads the SKILL.md metadata from the skills directory
        2. Loads configuration from environment variables
        3. Registers all six Firecrawl tools
        """
        if self._loaded:
            logger.debug("Firecrawl skill already loaded, skipping")
            return

        logger.info("Loading Firecrawl skill...")

        # Load skill metadata if SKILL.md exists
        skill_md_path = os.path.join(_SKILLS_DIR, "SKILL.md")
        if os.path.isfile(skill_md_path):
            try:
                import frontmatter
                with open(skill_md_path, "r", encoding="utf-8") as f:
                    content = frontmatter.load(f)
                self._skill_metadata = Skill(
                    name=str(content.get("name", "firecrawl")),
                    description=str(content.get("description", "")),
                    dir=_SKILLS_DIR,
                    markdown=content.content or "",
                    updated_at=os.path.getmtime(skill_md_path),
                )
                logger.info("Loaded Firecrawl skill metadata from %s", skill_md_path)
            except Exception as e:
                logger.warning("Failed to load SKILL.md: %s", e)

        # Load configuration from environment
        self._load_config_from_env()

        # Register tools
        self._register_tools()

        self._loaded = True
        logger.info(
            "Firecrawl skill loaded with %d tools (API key: %s)",
            len(self._tools),
            "configured" if self._config.api_key else "not configured",
        )

    def _load_config_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_api_key = os.environ.get("FIRECRAWL_API_KEY", "")
        env_endpoint = os.environ.get("FIRECRAWL_API_ENDPOINT", "")
        env_timeout = os.environ.get("FIRECRAWL_TIMEOUT_SECONDS", "")
        env_concurrency = os.environ.get("FIRECRAWL_MAX_CONCURRENT_CRAWLS", "")
        env_rate_limit = os.environ.get("FIRECRAWL_RATE_LIMIT_PER_MINUTE", "")
        env_max_pages = os.environ.get("FIRECRAWL_DEFAULT_MAX_PAGES", "")
        env_robots = os.environ.get("FIRECRAWL_RESPECT_ROBOTS_TXT", "")
        env_ua = os.environ.get("FIRECRAWL_USER_AGENT", "")

        if env_api_key:
            self._config.api_key = env_api_key
        if env_endpoint:
            self._config.api_endpoint = env_endpoint
        if env_timeout:
            try:
                self._config.timeout_seconds = int(env_timeout)
            except ValueError:
                pass
        if env_concurrency:
            try:
                self._config.max_concurrent_crawls = int(env_concurrency)
            except ValueError:
                pass
        if env_rate_limit:
            try:
                self._config.rate_limit_per_minute = int(env_rate_limit)
            except ValueError:
                pass
        if env_max_pages:
            try:
                self._config.default_max_pages = int(env_max_pages)
            except ValueError:
                pass
        if env_robots:
            self._config.respect_robots_txt = env_robots.lower() in ("true", "1", "yes")
        if env_ua:
            self._config.user_agent = env_ua

    def _register_tools(self) -> None:
        """Register all Firecrawl tools.

        Registers six tools: scrape, crawl, search, map, extract, parse.
        Each tool is registered with its name, description, and input schema.
        """
        # Import here to avoid circular imports
        from skpl_agent.app._service.firecrawl_service import FirecrawlService

        service = FirecrawlService(self._config)

        # Register each tool as a callable wrapper
        self._tools = {
            "scrape": self._make_scrape_tool(service),
            "crawl": self._make_crawl_tool(service),
            "search": self._make_search_tool(service),
            "map": self._make_map_tool(service),
            "extract": self._make_extract_tool(service),
            "parse": self._make_parse_tool(service),
        }

    # ── Tool Factory Methods ─────────────────────────────────────────────

    def _make_scrape_tool(self, service: Any) -> dict[str, Any]:
        """Create a scrape tool wrapper."""
        from skpl_agent.skills.firecrawl.tools.scrape import Scraper

        scraper = Scraper(self._config)

        async def scrape(url: str, formats: list[str] | None = None, only_main_content: bool = True, wait_for: int = 0) -> dict[str, Any]:
            """Scrape a single URL and extract content."""
            result = await scraper.scrape(url)
            return {
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
            }

        return {
            "name": "scrape",
            "description": "Scrape a single URL and extract content as markdown, HTML, and text.",
            "callable": scrape,
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to scrape"},
                    "formats": {"type": "array", "items": {"type": "string"}, "description": "Output formats"},
                    "only_main_content": {"type": "boolean", "description": "Extract only main content"},
                    "wait_for": {"type": "integer", "description": "Wait time in ms for JS rendering"},
                },
                "required": ["url"],
            },
        }

    def _make_crawl_tool(self, service: Any) -> dict[str, Any]:
        """Create a crawl tool wrapper."""
        from skpl_agent.skills.firecrawl.tools.crawl import Crawler

        crawler = Crawler(self._config)

        async def crawl(url: str, max_depth: int = 2, max_pages: int = 50, include_patterns: list[str] | None = None, exclude_patterns: list[str] | None = None) -> dict[str, Any]:
            """Crawl a website recursively."""
            result = await crawler.crawl(url, max_depth=max_depth, max_pages=max_pages, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
            return {
                "url": result.url,
                "status": result.status,
                "pages_scraped": result.pages_scraped,
                "pages_failed": result.pages_failed,
                "results": [
                    {
                        "url": r.url,
                        "title": r.title,
                        "content_markdown": r.content_markdown,
                    }
                    for r in result.results
                ],
                "error": result.error,
                "duration_ms": result.duration_ms,
            }

        return {
            "name": "crawl",
            "description": "Crawl a website recursively, following internal links.",
            "callable": crawl,
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Starting URL"},
                    "max_depth": {"type": "integer", "description": "Maximum crawl depth", "default": 2},
                    "max_pages": {"type": "integer", "description": "Maximum pages to crawl", "default": 50},
                    "include_patterns": {"type": "array", "items": {"type": "string"}, "description": "URL patterns to include"},
                    "exclude_patterns": {"type": "array", "items": {"type": "string"}, "description": "URL patterns to exclude"},
                },
                "required": ["url"],
            },
        }

    def _make_search_tool(self, service: Any) -> dict[str, Any]:
        """Create a search tool wrapper."""
        from skpl_agent.skills.firecrawl.tools.search import Searcher

        searcher = Searcher(self._config)

        async def search(query: str, engine: str = "google", num_results: int = 10, language: str = "en", country: str = "") -> dict[str, Any]:
            """Search the web."""
            results = await searcher.search(query, engine=engine, num_results=num_results, language=language, country=country)
            return {
                "query": results.query,
                "engine": results.engine,
                "results": [
                    {"title": r.title, "url": r.url, "snippet": r.snippet, "position": r.position, "domain": r.domain}
                    for r in results.results
                ],
                "total_results": results.total_results,
                "duration_ms": results.duration_ms,
                "error": results.error,
            }

        return {
            "name": "search",
            "description": "Search the web using integrated search engines.",
            "callable": search,
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "engine": {"type": "string", "description": "Search engine (google, bing)", "default": "google"},
                    "num_results": {"type": "integer", "description": "Max results", "default": 10},
                    "language": {"type": "string", "description": "Language code", "default": "en"},
                    "country": {"type": "string", "description": "Country code", "default": ""},
                },
                "required": ["query"],
            },
        }

    def _make_map_tool(self, service: Any) -> dict[str, Any]:
        """Create a site map tool wrapper."""
        from skpl_agent.skills.firecrawl.tools.map import SiteMapper

        mapper = SiteMapper(self._config)

        async def map_site(url: str, max_pages: int = 500, include_subdomains: bool = False) -> dict[str, Any]:
            """Discover all URLs on a website."""
            result = await mapper.map(url, max_pages=max_pages, include_subdomains=include_subdomains)
            return {
                "url": result.url,
                "status": result.status,
                "pages": result.pages,
                "total_pages": result.total_pages,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }

        return {
            "name": "map",
            "description": "Discover all URLs on a website via sitemap or link crawling.",
            "callable": map_site,
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Website URL to map"},
                    "max_pages": {"type": "integer", "description": "Max URLs to discover", "default": 500},
                    "include_subdomains": {"type": "boolean", "description": "Include subdomains", "default": False},
                },
                "required": ["url"],
            },
        }

    def _make_extract_tool(self, service: Any) -> dict[str, Any]:
        """Create an extract tool wrapper."""
        from skpl_agent.skills.firecrawl.tools.extract import Extractor

        extractor = Extractor(self._config)

        async def extract(url: str, schema: dict[str, Any], use_llm: bool = False, llm_prompt: str = "") -> dict[str, Any]:
            """Extract structured data from a URL."""
            result = await extractor.extract(url, schema, use_llm=use_llm, llm_prompt=llm_prompt)
            return {
                "url": result.url,
                "data": result.data,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }

        return {
            "name": "extract",
            "description": "Extract structured data from a web page using CSS selectors or LLM.",
            "callable": extract,
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to extract from"},
                    "schema": {"type": "object", "description": "Extraction schema"},
                    "use_llm": {"type": "boolean", "description": "Use LLM for extraction", "default": False},
                    "llm_prompt": {"type": "string", "description": "Additional LLM prompt", "default": ""},
                },
                "required": ["url", "schema"],
            },
        }

    def _make_parse_tool(self, service: Any) -> dict[str, Any]:
        """Create a parse tool wrapper."""
        from skpl_agent.skills.firecrawl.tools.parse import Parser

        parser = Parser()

        async def parse_content(content: str, content_type: str = "html", url: str = "") -> dict[str, Any]:
            """Parse content into structured formats."""
            if content_type == "html":
                result = parser.parse_html(content, url)
            elif content_type == "markdown":
                result = parser.parse_markdown(content)
            elif content_type == "text":
                result = parser.parse_text(content)
            else:
                return {"error": f"Unsupported content type: {content_type}"}

            return {
                "content_type": result.content_type,
                "text": result.text,
                "markdown": result.markdown,
                "html": result.html,
                "json_ld": result.json_ld,
                "tables": result.tables,
                "statistics": result.statistics,
                "error": result.error,
            }

        return {
            "name": "parse",
            "description": "Parse content into structured formats (HTML, text, markdown, PDF).",
            "callable": parse_content,
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Raw content to parse"},
                    "content_type": {"type": "string", "description": "Content type: html, text, markdown, pdf", "default": "html"},
                    "url": {"type": "string", "description": "Source URL for link resolution", "default": ""},
                },
                "required": ["content"],
            },
        }

    # ── Public API ───────────────────────────────────────────────────────

    def get_tools(self) -> dict[str, Any]:
        """Get all registered tools.

        Returns:
            Dict mapping tool names to tool definitions (name, description,
            callable, input_schema).
        """
        if not self._loaded:
            raise RuntimeError("FirecrawlSkill not loaded. Call load() first.")
        return self._tools

    def get_tool(self, name: str) -> Any | None:
        """Get a specific tool by name.

        Args:
            name: Tool name (scrape, crawl, search, map, extract, parse).

        Returns:
            Tool definition dict or None if not found.
        """
        return self._tools.get(name)

    async def update_config(self, **kwargs: Any) -> FirecrawlConfig:
        """Update the Firecrawl configuration.

        Args:
            **kwargs: Configuration key-value pairs to update.

        Returns:
            Updated FirecrawlConfig.
        """
        valid_keys = {
            "api_key", "api_endpoint", "max_concurrent_crawls",
            "rate_limit_per_minute", "default_max_pages",
            "timeout_seconds", "respect_robots_txt", "user_agent",
        }
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self._config, key, value)
                logger.info("Updated Firecrawl config: %s = %s", key, value)
            else:
                logger.warning("Ignored unknown config key: %s", key)

        return self._config

    async def unload(self) -> None:
        """Unload the skill and release resources."""
        self._tools.clear()
        self._loaded = False
        self._skill_metadata = None
        logger.info("Firecrawl skill unloaded")