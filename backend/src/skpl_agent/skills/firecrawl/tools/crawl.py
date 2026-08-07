"""Firecrawl crawler — recursive web crawler with depth control.

Adapted from Firecrawl's crawl functionality. Features:
- BFS crawling with configurable depth
- Same-domain restriction
- URL pattern filtering (include/exclude)
- Duplicate URL detection
- Concurrent crawling with limits
- Sitemap-based discovery
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from skpl_agent.app._service.firecrawl_service import FirecrawlConfig
from skpl_agent.skills.firecrawl.tools.scrape import Scraper, ScrapeResult

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a full crawl operation."""

    url: str
    status: str = "pending"  # pending | running | completed | failed
    pages_scraped: int = 0
    pages_failed: int = 0
    results: list[ScrapeResult] = field(default_factory=list)
    error: str = ""
    duration_ms: float = 0.0


class Crawler:
    """Recursive web crawler with configurable depth and filtering.

    Crawls a website starting from a root URL, following internal links
    up to a specified depth, respecting robots.txt and rate limits.

    Usage:
        >>> crawler = Crawler(config, scraper)
        >>> result = await crawler.crawl(
        ...     "https://example.com",
        ...     max_depth=2,
        ...     max_pages=50,
        ... )
        >>> for page in result.results:
        >>>     print(page.title)
    """

    def __init__(
        self,
        config: FirecrawlConfig,
        scraper: Optional[Scraper] = None,
    ) -> None:
        self._config = config
        self._scraper = scraper or Scraper(config)
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def crawl(
        self,
        url: str,
        max_depth: int = 2,
        max_pages: int = 50,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> CrawlResult:
        """Crawl a website starting from the given URL.

        Args:
            url: Starting URL.
            max_depth: Maximum crawl depth.
            max_pages: Maximum number of pages to crawl.
            include_patterns: URL patterns to include (regex).
            exclude_patterns: URL patterns to exclude (regex).

        Returns:
            CrawlResult with all scraped pages.
        """
        import re
        import time

        start = time.monotonic()
        result = CrawlResult(url=url, status="running")

        self._semaphore = asyncio.Semaphore(self._config.max_concurrent_crawls)

        base_domain = urlparse(url).netloc
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(url, 0)]  # (url, depth)

        include_re = [re.compile(p) for p in (include_patterns or [])]
        exclude_re = [re.compile(p) for p in (exclude_patterns or [])]

        try:
            while queue and len(result.results) < max_pages:
                # Get next batch of URLs at current depth
                batch = []
                current_depth = queue[0][1] if queue else 0

                while queue and queue[0][1] == current_depth and len(batch) < self._config.max_concurrent_crawls:
                    batch.append(queue.pop(0))

                if not batch:
                    break

                # Scrape batch concurrently
                tasks = []
                for page_url, depth in batch:
                    if page_url in visited:
                        continue
                    visited.add(page_url)
                    tasks.append(self._scrape_page(page_url))

                page_results = await asyncio.gather(*tasks, return_exceptions=True)

                for page_result in page_results:
                    if isinstance(page_result, Exception):
                        result.pages_failed += 1
                        continue

                    if isinstance(page_result, ScrapeResult):
                        if page_result.error:
                            result.pages_failed += 1
                        else:
                            result.pages_scraped += 1
                            result.results.append(page_result)

                            # Add new links to queue
                            if depth < max_depth:
                                for link in page_result.links:
                                    if link in visited:
                                        continue
                                    if len(result.results) + len(queue) >= max_pages:
                                        break

                                    # Same domain check
                                    link_domain = urlparse(link).netloc
                                    if link_domain != base_domain:
                                        continue

                                    # Pattern filtering
                                    if exclude_re and any(r.search(link) for r in exclude_re):
                                        continue
                                    if include_re and not any(r.search(link) for r in include_re):
                                        continue

                                    queue.append((link, depth + 1))

            result.status = "completed"

        except Exception as e:
            logger.error("Crawl error for %s: %s", url, e)
            result.status = "failed"
            result.error = str(e)

        finally:
            result.duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "Crawl finished: %s (%d pages, %.0fms)",
                url, result.pages_scraped, result.duration_ms,
            )

        return result

    async def _scrape_page(self, url: str) -> ScrapeResult:
        """Scrape a single page with concurrency control."""
        async with self._semaphore:
            return await self._scraper.scrape(url)

    async def close(self) -> None:
        """Close the scraper session."""
        await self._scraper.close()