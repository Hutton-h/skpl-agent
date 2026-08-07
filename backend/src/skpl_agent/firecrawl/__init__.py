"""Firecrawl skill module — web crawling and scraping integration.

Provides the Firecrawl skill as a standalone module, wrapping the
Firecrawl API for web crawling, content extraction, and site mapping.
Now uses the real Firecrawl tools implementation.

Usage::

    from skpl_agent.firecrawl import FirecrawlSkill

    skill = FirecrawlSkill(api_key="fc-...")
    result = await skill.crawl("https://example.com")
"""

from skpl_agent.app._service.firecrawl_service import (
    CrawlRequest,
    CrawlResult,
    FirecrawlConfig,
    FirecrawlService,
)
from skpl_agent.skills.firecrawl.tools import (
    Scraper,
    ScrapeResult,
    Crawler,
    Searcher,
    SearchResult,
    SearchResponse,
    SiteMapper,
    SiteMapResult,
    Extractor,
    ExtractResult,
    Parser,
    ParseResult,
)

__all__ = [
    # Service layer
    "CrawlRequest",
    "CrawlResult",
    "FirecrawlConfig",
    "FirecrawlService",
    # Tools
    "Scraper",
    "ScrapeResult",
    "Crawler",
    "Searcher",
    "SearchResult",
    "SearchResponse",
    "SiteMapper",
    "SiteMapResult",
    "Extractor",
    "ExtractResult",
    "Parser",
    "ParseResult",
]