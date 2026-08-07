"""Knowledge retrieval and fusion.

Adapted from Agent-S gui_agents/s1/core/Knowledge.py.
Provides query formulation, knowledge retrieval with caching,
and multi-source knowledge fusion.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from skpl_agent.web_intelligence._search_engine import (
    SearchEngine,
    SearchResult,
    DuckDuckGoEngine,
)

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBaseConfig:
    """Configuration for the knowledge base."""

    cache_dir: str = "./data/knowledge_cache"
    default_engine: str = "duckduckgo"  # duckduckgo | perplexica | llm
    max_cache_age_days: int = 7


class KnowledgeBase:
    """Knowledge retrieval and fusion system.

    Features:
    - Multi-engine search with caching
    - Query formulation (LLM-based)
    - Knowledge fusion (merge web + experience results)
    - Embedding-based similar task retrieval
    """

    def __init__(self, config: KnowledgeBaseConfig | None = None) -> None:
        self._config = config or KnowledgeBaseConfig()
        self._engines: dict[str, SearchEngine] = {}
        self._cache: dict[str, list[SearchResult]] = {}
        os.makedirs(self._config.cache_dir, exist_ok=True)

    # ── Engine management ────────────────────────────────────────────────

    def register_engine(self, engine: SearchEngine) -> None:
        """Register a search engine by name."""
        self._engines[engine.name] = engine
        logger.info("Registered search engine: %s", engine.name)

    def _get_engine(self, name: str | None = None) -> SearchEngine:
        """Get a search engine by name, falling back to default."""
        engine_name = name or self._config.default_engine
        if engine_name not in self._engines:
            # Auto-register default engines
            if engine_name == "duckduckgo":
                self.register_engine(DuckDuckGoEngine())
            elif engine_name == "perplexica":
                from skpl_agent.web_intelligence._search_engine import PerplexicaEngine
                self.register_engine(PerplexicaEngine())
            elif engine_name == "llm":
                from skpl_agent.web_intelligence._search_engine import LLMSearchEngine
                self.register_engine(LLMSearchEngine())
        return self._engines[engine_name]

    # ── Search ───────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        engine: str | None = None,
        num_results: int = 5,
        use_cache: bool = True,
    ) -> list[SearchResult]:
        """Execute a search query against the configured engine."""
        cache_key = f"{engine or self._config.default_engine}:{query}"

        if use_cache and cache_key in self._cache:
            logger.debug("Cache hit for query: %s", query)
            return self._cache[cache_key]

        engine_instance = self._get_engine(engine)
        results = await engine_instance.search(query, num_results=num_results)

        # Only cache non-empty results to avoid permanently caching
        # transient failures or rate-limited empty responses.
        if use_cache and results:
            self._cache[cache_key] = results
            self._save_cache()

        return results

    # ── Knowledge retrieval (Agent-S compatible) ─────────────────────────

    async def retrieve_knowledge(
        self,
        instruction: str,
        search_query: str | None = None,
        search_engine: str | None = None,
    ) -> tuple[str, list[SearchResult]]:
        """Retrieve knowledge for a given instruction.

        Args:
            instruction: The task instruction.
            search_query: Optional pre-formulated query. If None, uses instruction.
            search_engine: Engine name override.

        Returns:
            (query_used, search_results) tuple.
        """
        query = search_query or instruction
        results = await self.search(query, engine=search_engine)
        return query, results

    # ── Knowledge fusion ─────────────────────────────────────────────────

    def fuse_knowledge(
        self,
        instruction: str,
        web_results: list[SearchResult],
        similar_experiences: list[dict[str, str]] | None = None,
    ) -> str:
        """Fuse web search results with similar task experiences.

        Args:
            instruction: The original task instruction.
            web_results: Results from web search.
            similar_experiences: Optional similar task experiences.

        Returns:
            Fused knowledge text suitable for injection into agent context.
        """
        parts: list[str] = []

        if web_results:
            parts.append("## Web Search Results\n")
            for i, r in enumerate(web_results, 1):
                parts.append(f"{i}. **{r.title}**\n   {r.snippet}\n   [{r.url}]({r.url})" if r.url else f"{i}. **{r.title}**\n   {r.snippet}")

        if similar_experiences:
            parts.append("\n## Similar Task Experiences\n")
            for exp in similar_experiences:
                parts.append(f"- **{exp.get('task', 'Unknown')}**: {exp.get('result', '')}")

        if not parts:
            return f"No knowledge found for: {instruction}"

        return "\n".join(parts)

    # ── Cache persistence ────────────────────────────────────────────────

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        cache_path = os.path.join(self._config.cache_dir, "search_cache.json")
        try:
            serializable = {
                k: [
                    {"title": r.title, "url": r.url, "snippet": r.snippet, "source": r.source}
                    for r in v
                ]
                for k, v in self._cache.items()
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to save search cache: %s", e)

    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_path = os.path.join(self._config.cache_dir, "search_cache.json")
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache = {
                k: [
                    SearchResult(
                        title=r["title"], url=r.get("url", ""),
                        snippet=r["snippet"], source=r.get("source", ""),
                    )
                    for r in v
                ]
                for k, v in data.items()
            }
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning("Failed to load search cache: %s", e)