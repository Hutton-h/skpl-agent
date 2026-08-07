"""Web Intelligence service layer.

Manages search, knowledge retrieval, and research task orchestration.
"""

from __future__ import annotations

import logging
from typing import Any

from skpl_agent.web_intelligence import (
    KnowledgeBase,
    KnowledgeBaseConfig,
    ResearchAgent,
    ResearchConfig,
    ResearchTask,
    ResearchResult,
    SearchResult,
)

logger = logging.getLogger(__name__)


class WebIntelligenceService:
    """Service for web search, knowledge retrieval, and research.

    Wraps KnowledgeBase and ResearchAgent with session-aware
    caching and task lifecycle management.
    """

    def __init__(self) -> None:
        self._kb = KnowledgeBase(KnowledgeBaseConfig())
        self._research_agent = ResearchAgent(
            knowledge_base=self._kb,
            config=ResearchConfig(knowledge_base=self._kb),
        )

    # ── Search ───────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        engine: str | None = None,
        num_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Execute a web search query."""
        results = await self._kb.search(
            query, engine=engine, num_results=num_results
        )
        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "source": r.source,
            }
            for r in results
        ]

    # ── Knowledge Retrieval ──────────────────────────────────────────────

    async def retrieve_knowledge(
        self,
        instruction: str,
        search_query: str | None = None,
        engine: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve knowledge for a task instruction."""
        query, results = await self._kb.retrieve_knowledge(
            instruction, search_query=search_query, search_engine=engine
        )
        return {
            "query": query,
            "results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet, "source": r.source}
                for r in results
            ],
        }

    # ── Research ─────────────────────────────────────────────────────────

    async def start_research(
        self,
        query: str,
        context: str = "",
        max_sources: int | None = None,
    ) -> dict[str, Any]:
        """Start a multi-step research task."""
        result = await self._research_agent.research(
            query, context=context, max_sources=max_sources
        )
        return {
            "task_id": result.task_id,
            "query": result.query,
            "synthesis": result.synthesis,
            "sources": [
                {"title": s.title, "url": s.url, "snippet": s.snippet, "source": s.source}
                for s in result.sources
            ],
            "sub_queries_used": result.sub_queries_used,
            "iterations": result.iterations,
            "duration_seconds": result.duration_seconds,
        }

    async def get_research_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the status of a research task."""
        task = self._research_agent.get_task(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "query": task.query,
            "status": task.status,
            "sub_queries": task.sub_queries,
            "sources_count": len(task.sources),
            "synthesis": task.synthesis,
        }

    async def list_research_tasks(self) -> list[dict[str, Any]]:
        """List all research tasks."""
        return [
            {
                "task_id": t.task_id,
                "query": t.query,
                "status": t.status,
                "sources_count": len(t.sources),
            }
            for t in self._research_agent.list_tasks()
        ]

    # ── Engine management ────────────────────────────────────────────────

    async def get_available_engines(self) -> list[str]:
        """List available search engines."""
        return list(self._kb._engines.keys()) or ["duckduckgo", "perplexica", "llm"]