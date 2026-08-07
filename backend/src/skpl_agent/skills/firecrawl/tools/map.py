"""Firecrawl site map — discover all URLs on a website.

Provides URL discovery via:
- Sitemap.xml parsing
- Internal link crawling
- URL hierarchy reconstruction
"""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from skpl_agent.app._service.firecrawl_service import FirecrawlConfig
from skpl_agent.skills.firecrawl.tools.scrape import Scraper, ScrapeResult

logger = logging.getLogger(__name__)


@dataclass
class SiteMapResult:
    """Result of site mapping."""

    url: str
    status: str = "pending"
    pages: list[dict[str, Any]] = field(default_factory=list)
    total_pages: int = 0
    error: str = ""
    duration_ms: float = 0.0


class SiteMapper:
    """Discovers URLs on a website via sitemap and link crawling.

    Usage:
        >>> mapper = SiteMapper(config, scraper)
        >>> result = await mapper.map("https://example.com")
        >>> for page in result.pages:
        >>>     print(page["url"], page["title"])
    """

    def __init__(
        self,
        config: FirecrawlConfig,
        scraper: Optional[Scraper] = None,
    ) -> None:
        self._config = config
        self._scraper = scraper or Scraper(config)

    async def map(
        self,
        url: str,
        max_pages: int = 500,
        include_subdomains: bool = False,
    ) -> SiteMapResult:
        """Discover URLs on a website.

        Args:
            url: Starting URL.
            max_pages: Maximum number of URLs to discover.
            include_subdomains: Whether to include subdomain URLs.

        Returns:
            SiteMapResult with discovered pages.
        """
        import time
        start = time.monotonic()
        result = SiteMapResult(url=url)

        base_domain = urlparse(url).netloc

        try:
            # Try sitemap first
            sitemap_urls = await self._discover_sitemap(url)
            if sitemap_urls:
                logger.info("Found %d URLs via sitemap", len(sitemap_urls))
                result.pages = sitemap_urls[:max_pages]
                result.total_pages = len(sitemap_urls)
            else:
                # Fallback: crawl the homepage and extract links
                logger.info("No sitemap found, crawling homepage")
                result.pages = await self._crawl_homepage(url, max_pages)
                result.total_pages = len(result.pages)

            result.status = "completed"

        except Exception as e:
            logger.error("Site map error for %s: %s", url, e)
            result.status = "failed"
            result.error = str(e)

        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    async def _discover_sitemap(self, url: str) -> list[dict[str, Any]]:
        """Discover URLs from sitemap.xml."""
        sitemap_url = urljoin(url, "/sitemap.xml")
        urls: list[dict[str, Any]] = []

        try:
            scrape = await self._scraper.scrape(sitemap_url)
            if scrape.error:
                # Try robots.txt sitemap reference
                sitemap_urls = await self._get_sitemap_from_robots(url)
                urls = await self._parse_sitemaps(sitemap_urls)
            else:
                urls = self._parse_sitemap_xml(scrape.content_text)

        except Exception as e:
            logger.debug("Sitemap discovery failed: %s", e)

        return urls

    async def _get_sitemap_from_robots(self, url: str) -> list[str]:
        """Get sitemap URLs from robots.txt."""
        robots_url = urljoin(url, "/robots.txt")
        sitemap_urls: list[str] = []

        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            sitemap_urls = rp.site_maps() or []
        except Exception:
            pass

        return sitemap_urls

    async def _parse_sitemaps(self, sitemap_urls: list[str]) -> list[dict[str, Any]]:
        """Parse one or more sitemap files."""
        all_urls: list[dict[str, Any]] = []

        for sitemap_url in sitemap_urls:
            try:
                scrape = await self._scraper.scrape(sitemap_url)
                if not scrape.error:
                    urls = self._parse_sitemap_xml(scrape.content_text)
                    all_urls.extend(urls)
            except Exception:
                continue

        return all_urls

    def _parse_sitemap_xml(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse sitemap XML content."""
        urls: list[dict[str, Any]] = []

        try:
            root = ET.fromstring(xml_text)

            # Handle sitemap index
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            sitemap_tags = root.findall(".//sm:sitemap", ns) or root.findall(".//sitemap")

            if sitemap_tags:
                # This is a sitemap index — return the sitemap URLs for further processing
                for sitemap in sitemap_tags:
                    loc = sitemap.find("sm:loc", ns) or sitemap.find("loc")
                    if loc is not None and loc.text:
                        urls.append({"url": loc.text.strip(), "type": "sitemap"})
                return urls

            # Parse URL entries
            url_tags = root.findall(".//sm:url", ns) or root.findall(".//url")

            for url_tag in url_tags:
                entry: dict[str, Any] = {"type": "page"}

                loc = url_tag.find("sm:loc", ns) or url_tag.find("loc")
                if loc is not None and loc.text:
                    entry["url"] = loc.text.strip()

                lastmod = url_tag.find("sm:lastmod", ns) or url_tag.find("lastmod")
                if lastmod is not None and lastmod.text:
                    entry["last_modified"] = lastmod.text.strip()

                changefreq = url_tag.find("sm:changefreq", ns) or url_tag.find("changefreq")
                if changefreq is not None and changefreq.text:
                    entry["change_frequency"] = changefreq.text.strip()

                priority = url_tag.find("sm:priority", ns) or url_tag.find("priority")
                if priority is not None and priority.text:
                    try:
                        entry["priority"] = float(priority.text.strip())
                    except ValueError:
                        pass

                if "url" in entry:
                    urls.append(entry)

        except ET.ParseError:
            logger.debug("Failed to parse sitemap XML")
        except Exception as e:
            logger.debug("Sitemap parse error: %s", e)

        return urls

    async def _crawl_homepage(
        self, url: str, max_pages: int,
    ) -> list[dict[str, Any]]:
        """Crawl the homepage to discover URLs."""
        scrape = await self._scraper.scrape(url)
        if scrape.error:
            return []

        pages: list[dict[str, Any]] = [
            {
                "url": url,
                "title": scrape.title,
                "type": "page",
                "description": scrape.description,
            }
        ]

        base_domain = urlparse(url).netloc
        for link in scrape.links[:max_pages - 1]:
            link_domain = urlparse(link).netloc
            if link_domain == base_domain:
                pages.append({"url": link, "type": "page"})

        return pages

    async def close(self) -> None:
        await self._scraper.close()