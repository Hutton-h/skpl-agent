"""Firecrawl extract — structured data extraction from web pages.

Adapted from Firecrawl's extract functionality. Uses:
- LLM-powered extraction (via API)
- CSS/XPath selector-based extraction
- Schema-guided structured output
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from bs4 import BeautifulSoup

from skpl_agent.app._service.firecrawl_service import FirecrawlConfig
from skpl_agent.skills.firecrawl.tools.scrape import Scraper, ScrapeResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractResult:
    """Result of structured data extraction."""

    url: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0


class Extractor:
    """Extracts structured data from web pages using selectors or LLM.

    Supports two modes:
    1. Selector-based: Use CSS selectors to extract specific fields
    2. Schema-based: Define a JSON schema for LLM-powered extraction

    Usage:
        >>> extractor = Extractor(config, scraper)
        >>> result = await extractor.extract(
        ...     "https://example.com",
        ...     schema={"title": "h1", "price": ".price"},
        ... )
    """

    def __init__(
        self,
        config: FirecrawlConfig,
        scraper: Optional[Scraper] = None,
    ) -> None:
        self._config = config
        self._scraper = scraper or Scraper(config)

    async def extract(
        self,
        url: str,
        schema: dict[str, Any],
        use_llm: bool = False,
        llm_prompt: str = "",
    ) -> ExtractResult:
        """Extract structured data from a URL.

        Args:
            url: URL to extract from.
            schema: Extraction schema. Keys are field names, values are CSS
                    selectors (selector mode) or type descriptions (LLM mode).
            use_llm: Whether to use LLM for extraction.
            llm_prompt: Additional prompt for LLM extraction.

        Returns:
            ExtractResult with structured data.
        """
        import time
        start = time.monotonic()

        try:
            scrape = await self._scraper.scrape(url)

            if scrape.error:
                return ExtractResult(
                    url=url,
                    error=scrape.error,
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            if use_llm:
                data = await self._extract_with_llm(scrape, schema, llm_prompt)
            else:
                data = self._extract_with_selectors(scrape.content_html, schema)

            elapsed = (time.monotonic() - start) * 1000

            return ExtractResult(
                url=url,
                data=data,
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error("Extract error for %s: %s", url, e)
            return ExtractResult(
                url=url,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    def _extract_with_selectors(
        self, html: str, schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract data using CSS selectors.

        Each schema value can be:
        - A CSS selector string (e.g., "h1", ".price")
        - A dict with "selector" and optional "attribute" keys
        - A dict with "selector" and "multiple" (True) for lists
        """
        soup = BeautifulSoup(html, "lxml")
        result: dict[str, Any] = {}

        for field_name, field_config in schema.items():
            if isinstance(field_config, str):
                # Simple selector
                elem = soup.select_one(field_config)
                if elem:
                    result[field_name] = elem.get_text(strip=True)
                else:
                    result[field_name] = None

            elif isinstance(field_config, dict):
                selector = field_config.get("selector", "")
                attribute = field_config.get("attribute", "")
                multiple = field_config.get("multiple", False)

                if multiple:
                    elems = soup.select(selector)
                    if attribute:
                        result[field_name] = [
                            e.get(attribute, "") for e in elems
                        ]
                    else:
                        result[field_name] = [
                            e.get_text(strip=True) for e in elems
                        ]
                else:
                    elem = soup.select_one(selector)
                    if elem:
                        if attribute:
                            result[field_name] = elem.get(attribute, "")
                        else:
                            result[field_name] = elem.get_text(strip=True)
                    else:
                        result[field_name] = None

        return result

    async def _extract_with_llm(
        self,
        scrape: ScrapeResult,
        schema: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        """Extract data using LLM (requires API key).

        Sends the page content to an LLM with a schema description
        and returns structured JSON.
        """
        if not self._config.api_key:
            return {"error": "API key required for LLM extraction"}

        # Build the extraction prompt
        schema_desc = json.dumps(schema, indent=2)
        full_prompt = (
            f"Extract the following structured data from this web page.\n\n"
            f"Schema:\n{schema_desc}\n\n"
            f"{prompt}\n\n"
            f"Page Title: {scrape.title}\n"
            f"Page Content:\n{scrape.content_text[:8000]}\n\n"
            f"Return ONLY valid JSON matching the schema. No explanation."
        )

        try:
            import aiohttp

            headers = {
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": full_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 2000,
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self._config.api_endpoint}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        # Try to parse JSON from the response
                        content = content.strip()
                        if content.startswith("```"):
                            content = content.split("\n", 1)[1]
                            content = content.rsplit("\n```", 1)[0]
                        return json.loads(content)
                    else:
                        return {"error": f"LLM API error: {response.status}"}

        except Exception as e:
            logger.error("LLM extraction failed: %s", e)
            return {"error": str(e)}

    async def close(self) -> None:
        await self._scraper.close()