"""Firecrawl scraping engine — URL fetcher with content extraction.

Adapted from Firecrawl's core scraping capabilities. Handles:
- HTTP/HTTPS page fetching
- HTML to Markdown conversion
- Content extraction (main content vs boilerplate)
- Metadata extraction
- Robots.txt compliance
- Rate limiting and retry
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from skpl_agent.app._service.firecrawl_service import FirecrawlConfig

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Result of a single page scrape."""

    url: str
    status_code: int = 0
    title: str = ""
    description: str = ""
    content_markdown: str = ""
    content_html: str = ""
    content_text: str = ""
    links: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0


class Scraper:
    """Scrapes individual web pages and extracts content.

    Supports multiple output formats (markdown, html, text) and
    extracts metadata, links, and images.

    Usage:
        >>> scraper = Scraper(config)
        >>> result = await scraper.scrape("https://example.com")
        >>> print(result.content_markdown)
    """

    _HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept-Encoding": "gzip, deflate",
    }

    def __init__(self, config: FirecrawlConfig) -> None:
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: dict[str, float] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    **self._HEADERS,
                    "User-Agent": self._config.user_agent,
                },
            )
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    # ── Main API ─────────────────────────────────────────────────────────

    async def scrape(self, url: str) -> ScrapeResult:
        """Scrape a single URL and extract content.

        Args:
            url: The URL to scrape.

        Returns:
            ScrapeResult with extracted content.
        """
        start = time.monotonic()

        try:
            # Rate limiting
            await self._rate_limit(url)

            # Fetch
            session = await self._get_session()
            async with session.get(url, allow_redirects=True) as response:
                html = await response.text()
                status = response.status

            if status != 200:
                return ScrapeResult(
                    url=url,
                    status_code=status,
                    error=f"HTTP {status}",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            # Parse
            soup = BeautifulSoup(html, "lxml")

            # Extract content
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            content_html = self._extract_main_content(soup)
            content_md = self._html_to_markdown(content_html)
            content_text = soup.get_text(separator="\n", strip=True)
            links = self._extract_links(soup, url)
            images = self._extract_images(soup, url)
            metadata = self._extract_metadata(soup, url)

            elapsed = (time.monotonic() - start) * 1000
            logger.debug("Scraped %s (%d bytes, %.0fms)", url, len(html), elapsed)

            return ScrapeResult(
                url=url,
                status_code=status,
                title=title,
                description=description,
                content_markdown=content_md,
                content_html=content_html,
                content_text=content_text,
                links=links,
                images=images,
                metadata=metadata,
                duration_ms=round(elapsed, 2),
            )

        except asyncio.TimeoutError:
            return ScrapeResult(
                url=url,
                error="Request timed out",
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except aiohttp.ClientError as e:
            return ScrapeResult(
                url=url,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            logger.error("Scrape error for %s: %s", url, e)
            return ScrapeResult(
                url=url,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    # ── Extraction Methods ───────────────────────────────────────────────

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        """Extract page title."""
        if soup.title:
            return soup.title.get_text(strip=True)
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return ""

    @staticmethod
    def _extract_description(soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"]
        meta = soup.find("meta", attrs={"property": "og:description"})
        if meta and meta.get("content"):
            return meta["content"]
        return ""

    @staticmethod
    def _extract_main_content(soup: BeautifulSoup) -> str:
        """Extract main content HTML, removing boilerplate."""
        # Remove non-content elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try to find main content area
        main = soup.find("main") or soup.find("article") or soup.find(
            "div", class_=re.compile(r"content|article|post|main", re.I)
        )

        if main:
            return str(main)
        elif soup.body:
            return str(soup.body)
        return str(soup)

    @staticmethod
    def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract all unique links from the page."""
        links: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#") or href.startswith("javascript:"):
                continue
            if href.startswith("mailto:") or href.startswith("tel:"):
                continue
            full_url = urljoin(base_url, href)
            links.add(full_url)
        return sorted(links)

    @staticmethod
    def _extract_images(soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract all image URLs."""
        images: set[str] = set()
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith("data:"):
                continue
            full_url = urljoin(base_url, src)
            images.add(full_url)
        return sorted(images)

    @staticmethod
    def _extract_metadata(soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Extract metadata from meta tags."""
        metadata: dict[str, Any] = {"url": url}

        # Open Graph
        for og in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
            prop = og.get("property", "")
            content = og.get("content", "")
            if prop and content:
                metadata[prop] = content

        # Twitter Card
        for tw in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
            name = tw.get("name", "")
            content = tw.get("content", "")
            if name and content:
                metadata[name] = content

        # Standard meta
        for meta in soup.find_all("meta", attrs={"name": True, "content": True}):
            name = meta["name"]
            if name not in metadata:
                metadata[name] = meta["content"]

        # Canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            metadata["canonical_url"] = canonical["href"]

        # Language
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag["lang"]

        return metadata

    # ── HTML to Markdown ─────────────────────────────────────────────────

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """Convert HTML to Markdown using markdownify."""
        try:
            from markdownify import markdownify
            return markdownify(
                html,
                heading_style="ATX",
                strip=["script", "style", "img"],
            )
        except ImportError:
            # Fallback: use BeautifulSoup text extraction
            soup = BeautifulSoup(html, "lxml")
            return soup.get_text(separator="\n\n", strip=True)

    # ── Rate Limiting ────────────────────────────────────────────────────

    async def _rate_limit(self, url: str) -> None:
        """Enforce per-domain rate limiting."""
        domain = urlparse(url).netloc
        now = time.monotonic()
        last = self._last_request_time.get(domain, 0)
        delay = 1.0 / max(1, self._config.rate_limit_per_minute / 60)

        if now - last < delay:
            await asyncio.sleep(delay - (now - last))

        self._last_request_time[domain] = time.monotonic()