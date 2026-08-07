"""Firecrawl API client — HTTP client for the Firecrawl REST API.

Provides a typed Python wrapper around the Firecrawl API endpoints:
- /v1/scrape — Single page scraping
- /v1/crawl — Recursive website crawling
- /v1/search — Web search
- /v1/map — Site URL discovery
- /v1/extract — Structured data extraction
- /v1/parse — Content parsing

Supports synchronous and asynchronous usage, with automatic retry,
timeout handling, and error mapping.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_API_ENDPOINT = "https://api.firecrawl.dev"
_DEFAULT_TIMEOUT = 300.0  # seconds
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY = 1.0  # seconds
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class FirecrawlScrapeResult:
    """Result of a Firecrawl scrape operation."""

    url: str
    title: str = ""
    description: str = ""
    content: str = ""
    markdown: str = ""
    html: str = ""
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    status_code: int = 0
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class FirecrawlCrawlResult:
    """Result of a Firecrawl crawl operation."""

    job_id: str = ""
    url: str = ""
    status: str = "pending"  # pending | running | completed | failed
    pages: list[FirecrawlScrapeResult] = field(default_factory=list)
    total_pages: int = 0
    credits_used: int = 0
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class FirecrawlSearchResult:
    """Result of a Firecrawl search operation."""

    query: str
    results: list[dict[str, Any]] = field(default_factory=list)
    total_results: int = 0
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class FirecrawlMapResult:
    """Result of a Firecrawl map operation."""

    url: str
    links: list[str] = field(default_factory=list)
    total_links: int = 0
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class FirecrawlExtractResult:
    """Result of a Firecrawl extract operation."""

    url: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class FirecrawlParseResult:
    """Result of a Firecrawl parse operation."""

    content_type: str = ""
    text: str = ""
    markdown: str = ""
    html: str = ""
    json_ld: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FirecrawlClient:
    """HTTP client for the Firecrawl REST API.

    Features:
    - Async HTTP via httpx
    - Automatic retry with exponential backoff
    - Configurable timeout
    - Structured error handling
    - API key authentication

    Usage:
        >>> client = FirecrawlClient(api_key="fc-xxx")
        >>> result = await client.scrape("https://example.com")
        >>> print(result.markdown)
    """

    def __init__(
        self,
        api_key: str = "",
        api_endpoint: str = _DEFAULT_API_ENDPOINT,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_delay: float = _DEFAULT_RETRY_DELAY,
    ) -> None:
        """Initialize the Firecrawl API client.

        Args:
            api_key: Firecrawl API key. If empty, the client will operate
                     in local-only mode (no API calls).
            api_endpoint: Base URL of the Firecrawl API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts for failed requests.
            retry_delay: Base delay between retries (exponential backoff).
        """
        self._api_key = api_key
        self._api_endpoint = api_endpoint.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def has_api_key(self) -> bool:
        """Check if an API key is configured."""
        return bool(self._api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "SKPL-Agent-Firecrawl/0.1",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client session."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Request helpers ──────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path (e.g., "/v1/scrape").
            json_data: JSON body for POST/PUT requests.
            params: Query parameters for GET requests.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors.
            httpx.RequestError: On network errors after all retries.
        """
        if not self._api_key:
            raise ValueError(
                "Firecrawl API key is not configured. "
                "Set FIRECRAWL_API_KEY environment variable or pass api_key."
            )

        url = f"{self._api_endpoint}{path}"
        client = await self._get_client()

        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                )

                if response.status_code in _RETRYABLE_STATUSES and attempt < self._max_retries:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(
                        "Retryable status %d for %s %s, retrying in %.1fs (attempt %d/%d)",
                        response.status_code, method, path, delay, attempt + 1, self._max_retries,
                    )
                    await asyncio.sleep(delay)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code not in _RETRYABLE_STATUSES or attempt >= self._max_retries:
                    raise
                last_error = e
                delay = self._retry_delay * (2 ** attempt)
                logger.warning(
                    "HTTP %d for %s %s, retrying (attempt %d/%d)",
                    e.response.status_code, method, path, attempt + 1, self._max_retries,
                )
                await asyncio.sleep(delay)

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                if attempt < self._max_retries:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(
                        "Network error for %s %s: %s, retrying (attempt %d/%d)",
                        method, path, e, attempt + 1, self._max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        raise last_error  # type: ignore[misc]

    # ── Public API methods ───────────────────────────────────────────────

    async def scrape(
        self,
        url: str,
        formats: list[str] | None = None,
        only_main_content: bool = True,
        wait_for: int = 0,
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
    ) -> FirecrawlScrapeResult:
        """Scrape a single URL and extract content.

        Args:
            url: The URL to scrape.
            formats: Output formats to include (markdown, html, text).
            only_main_content: Extract only the main content.
            wait_for: Wait time in milliseconds for JS rendering.
            include_tags: HTML tags to include.
            exclude_tags: HTML tags to exclude.

        Returns:
            FirecrawlScrapeResult with extracted content.
        """
        start = time.monotonic()
        formats = formats or ["markdown"]

        try:
            data = await self._request(
                "POST",
                "/v1/scrape",
                json_data={
                    "url": url,
                    "formats": formats,
                    "onlyMainContent": only_main_content,
                    "waitFor": wait_for,
                    "includeTags": include_tags or [],
                    "excludeTags": exclude_tags or [],
                },
            )

            result_data = data.get("data", data)
            elapsed = (time.monotonic() - start) * 1000

            return FirecrawlScrapeResult(
                url=url,
                title=result_data.get("title", ""),
                description=result_data.get("description", ""),
                content=result_data.get("content", ""),
                markdown=result_data.get("markdown", ""),
                html=result_data.get("html", ""),
                text=result_data.get("text", ""),
                metadata=result_data.get("metadata", {}),
                links=result_data.get("links", []),
                images=result_data.get("images", []),
                status_code=result_data.get("statusCode", 200),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Scrape error for %s: %s", url, e)
            return FirecrawlScrapeResult(
                url=url,
                error=str(e),
                duration_ms=round(elapsed, 2),
            )

    async def crawl(
        self,
        url: str,
        max_depth: int = 2,
        max_pages: int = 50,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        scrape_formats: list[str] | None = None,
    ) -> FirecrawlCrawlResult:
        """Crawl a website recursively.

        Args:
            url: Starting URL.
            max_depth: Maximum crawl depth.
            max_pages: Maximum number of pages to crawl.
            include_patterns: URL patterns to include (regex).
            exclude_patterns: URL patterns to exclude (regex).
            scrape_formats: Output formats for each page.

        Returns:
            FirecrawlCrawlResult with all scraped pages.
        """
        start = time.monotonic()

        try:
            data = await self._request(
                "POST",
                "/v1/crawl",
                json_data={
                    "url": url,
                    "maxDepth": max_depth,
                    "limit": max_pages,
                    "includePaths": include_patterns or [],
                    "excludePaths": exclude_patterns or [],
                    "scrapeOptions": {
                        "formats": scrape_formats or ["markdown"],
                    },
                },
            )

            result_data = data.get("data", data)
            elapsed = (time.monotonic() - start) * 1000

            pages = []
            for page_data in result_data.get("pages", []):
                pages.append(FirecrawlScrapeResult(
                    url=page_data.get("url", ""),
                    title=page_data.get("title", ""),
                    markdown=page_data.get("markdown", ""),
                    html=page_data.get("html", ""),
                    metadata=page_data.get("metadata", {}),
                ))

            return FirecrawlCrawlResult(
                job_id=result_data.get("id", ""),
                url=url,
                status=result_data.get("status", "completed"),
                pages=pages,
                total_pages=len(pages),
                credits_used=result_data.get("creditsUsed", 0),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Crawl error for %s: %s", url, e)
            return FirecrawlCrawlResult(
                url=url,
                status="failed",
                error=str(e),
                duration_ms=round(elapsed, 2),
            )

    async def search(
        self,
        query: str,
        engine: str = "google",
        num_results: int = 10,
        language: str = "en",
        country: str = "",
    ) -> FirecrawlSearchResult:
        """Search the web using Firecrawl.

        Args:
            query: Search query string.
            engine: Search engine (google, bing).
            num_results: Maximum number of results.
            language: Language code.
            country: Country code.

        Returns:
            FirecrawlSearchResult with search results.
        """
        start = time.monotonic()

        try:
            data = await self._request(
                "POST",
                "/v1/search",
                json_data={
                    "query": query,
                    "engine": engine,
                    "limit": num_results,
                    "lang": language,
                    "country": country,
                },
            )

            result_data = data.get("data", data)
            elapsed = (time.monotonic() - start) * 1000

            return FirecrawlSearchResult(
                query=query,
                results=result_data.get("results", result_data.get("web", [])),
                total_results=result_data.get("totalResults", len(result_data.get("results", []))),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Search error for '%s': %s", query, e)
            return FirecrawlSearchResult(
                query=query,
                error=str(e),
                duration_ms=round(elapsed, 2),
            )

    async def map(
        self,
        url: str,
        max_pages: int = 500,
        include_subdomains: bool = False,
    ) -> FirecrawlMapResult:
        """Discover all URLs on a website.

        Args:
            url: Website URL to map.
            max_pages: Maximum number of URLs to discover.
            include_subdomains: Whether to include subdomain URLs.

        Returns:
            FirecrawlMapResult with discovered URLs.
        """
        start = time.monotonic()

        try:
            data = await self._request(
                "POST",
                "/v1/map",
                json_data={
                    "url": url,
                    "limit": max_pages,
                    "includeSubdomains": include_subdomains,
                },
            )

            result_data = data.get("data", data)
            elapsed = (time.monotonic() - start) * 1000
            links = result_data.get("links", result_data.get("urls", []))

            return FirecrawlMapResult(
                url=url,
                links=links,
                total_links=len(links),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Map error for %s: %s", url, e)
            return FirecrawlMapResult(
                url=url,
                error=str(e),
                duration_ms=round(elapsed, 2),
            )

    async def extract(
        self,
        url: str,
        schema: dict[str, Any],
        use_llm: bool = False,
        llm_prompt: str = "",
    ) -> FirecrawlExtractResult:
        """Extract structured data from a URL.

        Args:
            url: URL to extract from.
            schema: Extraction schema (field names to selectors or types).
            use_llm: Whether to use LLM for extraction.
            llm_prompt: Additional prompt for LLM extraction.

        Returns:
            FirecrawlExtractResult with structured data.
        """
        start = time.monotonic()

        try:
            json_data: dict[str, Any] = {
                "url": url,
                "schema": schema,
            }

            if use_llm:
                json_data["useLLM"] = True
                if llm_prompt:
                    json_data["prompt"] = llm_prompt

            data = await self._request("POST", "/v1/extract", json_data=json_data)

            result_data = data.get("data", data)
            elapsed = (time.monotonic() - start) * 1000

            return FirecrawlExtractResult(
                url=url,
                data=result_data.get("data", result_data),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Extract error for %s: %s", url, e)
            return FirecrawlExtractResult(
                url=url,
                error=str(e),
                duration_ms=round(elapsed, 2),
            )

    async def parse(
        self,
        url: str,
        content_type: str = "html",
    ) -> FirecrawlParseResult:
        """Parse content from a URL.

        Args:
            url: URL to parse content from.
            content_type: Type of content (html, pdf, markdown).

        Returns:
            FirecrawlParseResult with parsed content.
        """
        start = time.monotonic()

        try:
            data = await self._request(
                "POST",
                "/v1/parse",
                json_data={
                    "url": url,
                    "contentType": content_type,
                },
            )

            result_data = data.get("data", data)
            elapsed = (time.monotonic() - start) * 1000

            return FirecrawlParseResult(
                content_type=result_data.get("contentType", content_type),
                text=result_data.get("text", ""),
                markdown=result_data.get("markdown", ""),
                html=result_data.get("html", ""),
                json_ld=result_data.get("jsonLd", []),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Parse error for %s: %s", url, e)
            return FirecrawlParseResult(
                error=str(e),
                duration_ms=round(elapsed, 2),
            )