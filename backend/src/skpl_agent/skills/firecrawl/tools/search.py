"""Firecrawl search — search engine integration for web discovery.

Adapted from Firecrawl's search functionality. Features:
- Multi-engine search (Google, Bing, etc.)
- SERP parsing and result extraction
- Search result filtering and ranking
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote_plus, urlparse

from skpl_agent.app._service.firecrawl_service import FirecrawlConfig
from skpl_agent.skills.firecrawl.tools.scrape import Scraper

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str = ""
    position: int = 0
    domain: str = ""
    additional_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Complete search response."""

    query: str
    engine: str = "google"
    results: list[SearchResult] = field(default_factory=list)
    total_results: int = 0
    duration_ms: float = 0.0
    error: str = ""


class Searcher:
    """Web search engine integration.

    Currently supports Google (via scraping SERP) and can be extended
    with API-based search engines.

    Usage:
        >>> searcher = Searcher(config, scraper)
        >>> results = await searcher.search("python web scraping")
        >>> for r in results.results:
        >>>     print(r.title, r.url)
    """

    # Google SERP URL patterns
    _GOOGLE_SEARCH_URL = "https://www.google.com/search"
    _BING_SEARCH_URL = "https://www.bing.com/search"

    def __init__(
        self,
        config: FirecrawlConfig,
        scraper: Optional[Scraper] = None,
    ) -> None:
        self._config = config
        self._scraper = scraper or Scraper(config)

    async def search(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 10,
        language: str = "en",
        country: str = "",
    ) -> SearchResponse:
        """Execute a web search.

        Args:
            query: Search query string.
            engine: Search engine to use (google, bing).
            num_results: Maximum number of results to return.
            language: Language code (e.g., 'en', 'zh-CN').
            country: Country code for localized results.

        Returns:
            SearchResponse with results.
        """
        import time
        start = time.monotonic()

        used_engine = engine
        if engine == "google":
            results = await self._search_google(query, num_results, language, country)
            if not results:
                logger.info("Google returned no results, falling back to Bing")
                results = await self._search_bing(query, num_results, language, country)
                used_engine = "bing"
        elif engine == "bing":
            results = await self._search_bing(query, num_results, language, country)
        else:
            return SearchResponse(
                query=query,
                engine=engine,
                error=f"Unsupported search engine: {engine}",
            )

        elapsed = (time.monotonic() - start) * 1000

        return SearchResponse(
            query=query,
            engine=used_engine,
            results=results[:num_results],
            total_results=len(results),
            duration_ms=round(elapsed, 2),
        )

    async def _search_google(
        self,
        query: str,
        num_results: int,
        language: str,
        country: str,
    ) -> list[SearchResult]:
        """Search Google via HTML scraping."""
        params = {
            "q": query,
            "num": min(num_results, 100),
            "hl": language,
        }
        if country:
            params["gl"] = country

        query_string = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        search_url = f"{self._GOOGLE_SEARCH_URL}?{query_string}"

        try:
            scrape_result = await self._scraper.scrape(search_url)

            if scrape_result.error:
                logger.warning("Google search failed: %s", scrape_result.error)
                return []

            # Parse SERP HTML
            results = self._parse_google_serp(scrape_result.content_html)
            return results

        except Exception as e:
            logger.error("Search error: %s", e)
            return []

    def _parse_google_serp(self, html: str) -> list[SearchResult]:
        """Parse Google search results from HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []

        # Google SERP result selectors
        result_divs = soup.find_all("div", class_=re.compile(r"^g$|^Gx5Zad"))

        position = 0
        for div in result_divs:
            # Title and link
            link_elem = div.find("a")
            if not link_elem:
                continue

            url = link_elem.get("href", "")
            if url.startswith("/url?"):
                # Extract actual URL from Google redirect
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query)
                url = qs.get("q", [url])[0]

            title = ""
            h3 = div.find("h3")
            if h3:
                title = h3.get_text(strip=True)

            # Snippet
            snippet = ""
            snippet_div = div.find("div", class_=re.compile(r"VwiC3b|IsZvec"))
            if snippet_div:
                snippet = snippet_div.get_text(strip=True)

            if title and url:
                domain = urlparse(url).netloc
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    position=position,
                    domain=domain,
                ))
                position += 1

        return results

    async def _search_bing(
        self,
        query: str,
        num_results: int,
        language: str,
        country: str,
    ) -> list[SearchResult]:
        """Search Bing via HTML scraping."""
        params = {
            "q": query,
            "count": min(num_results, 50),
        }
        if language:
            params["setlang"] = language
        if country:
            params["cc"] = country

        query_string = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        search_url = f"{self._BING_SEARCH_URL}?{query_string}"

        try:
            scrape_result = await self._scraper.scrape(search_url)

            if scrape_result.error:
                logger.warning("Bing search failed: %s", scrape_result.error)
                return []

            results = self._parse_bing_serp(scrape_result.content_html)
            return results

        except Exception as e:
            logger.error("Bing search error: %s", e)
            return []

    def _parse_bing_serp(self, html: str) -> list[SearchResult]:
        """Parse Bing search results from HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []
        position = 0

        # Bing SERP result selectors
        result_items = soup.find_all("li", class_=re.compile(r"b_algo"))

        for item in result_items:
            # Title and link
            title_elem = item.find("h2")
            if not title_elem:
                continue
            link_elem = title_elem.find("a")
            if not link_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = link_elem.get("href", "")

            # Snippet
            snippet = ""
            snippet_div = item.find("p")
            if snippet_div:
                snippet = snippet_div.get_text(strip=True)
            if not snippet:
                snippet_div = item.find("div", class_=re.compile(r"b_caption"))
                if snippet_div:
                    snippet = snippet_div.get_text(strip=True)

            if title and url:
                domain = urlparse(url).netloc
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    position=position,
                    domain=domain,
                ))
                position += 1

        return results

    async def close(self) -> None:
        """Close the scraper session."""
        await self._scraper.close()