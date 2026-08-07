"""Search engine abstraction layer.

Adapted from Agent-S gui_agents/s1/utils/query_perplexica.py and
gui_agents/s1/core/Knowledge.py.

Provides a uniform interface for multiple search backends:
- Perplexica (self-hosted)
- LLM (model's internal knowledge)
- DuckDuckGo (free, no API key)
- Google (Custom Search API)
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result item."""

    title: str
    url: str
    snippet: str
    source: str = ""


class SearchEngine(ABC):
    """Abstract base for search engine implementations."""

    name: str = "base"

    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Execute a search and return structured results."""
        ...


# ---------------------------------------------------------------------------
# Perplexica Engine
# ---------------------------------------------------------------------------

class PerplexicaEngine(SearchEngine):
    """Self-hosted Perplexica search engine.

    Requires PERPLEXICA_URL environment variable pointing to the
    Perplexica API endpoint (e.g. http://localhost:3001/api/search).
    """

    name = "perplexica"

    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.getenv("PERPLEXICA_URL", "")
        if not self._url:
            logger.warning("PERPLEXICA_URL not set; PerplexicaEngine will fail at runtime")

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        if not self._url:
            raise ValueError("PERPLEXICA_URL environment variable not set")

        payload = {
            "focusMode": "webSearch",
            "query": query,
            "history": [["human", query]],
        }

        try:
            response = requests.post(self._url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", "")

            return [SearchResult(
                title=query,
                url="",
                snippet=message,
                source="perplexica",
            )]
        except requests.RequestException as e:
            logger.error("Perplexica search failed: %s", e)
            raise


# ---------------------------------------------------------------------------
# LLM Search Engine
# ---------------------------------------------------------------------------

class LLMSearchEngine(SearchEngine):
    """Use an LLM's internal knowledge as a search engine.

    This is a lightweight fallback that doesn't require any external
    search API. The LLM generates answers from its training data.
    """

    name = "llm"

    def __init__(self, model_name: str = "gpt-4o") -> None:
        self._model_name = model_name

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        # In production, this would call the configured LLM.
        # For now, returns a placeholder.
        return [SearchResult(
            title=query,
            url="",
            snippet=f"[LLM search for: {query}] — configure an LLM backend for production use.",
            source="llm",
        )]


# ---------------------------------------------------------------------------
# DuckDuckGo Engine
# ---------------------------------------------------------------------------

class DuckDuckGoEngine(SearchEngine):
    """Free DuckDuckGo search via ddgs library (formerly duckduckgo_search).

    Install: pip install ddgs
    """

    name = "duckduckgo"

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        # Prefer the new ddgs library, fall back to legacy duckduckgo_search
        DDGS = None
        try:
            from ddgs import DDGS as NewDDGS
            DDGS = NewDDGS
        except ImportError:
            pass

        if DDGS is None:
            try:
                from duckduckgo_search import DDGS as LegacyDDGS
                DDGS = LegacyDDGS
            except ImportError:
                raise ImportError(
                    "ddgs (or duckduckgo_search) is required for DuckDuckGoEngine. "
                    "Install with: pip install ddgs"
                )

        results: list[SearchResult] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source="duckduckgo",
                    ))
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)

        return results