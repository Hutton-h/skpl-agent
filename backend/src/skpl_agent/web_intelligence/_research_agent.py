"""Multi-step research agent.

Orchestrates research tasks: query generation → search → synthesis.
Supports iterative refinement and citation tracking.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from skpl_agent.web_intelligence._knowledge_base import KnowledgeBase
from skpl_agent.web_intelligence._search_engine import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class ResearchConfig:
    """Configuration for the research agent."""

    max_iterations: int = 3
    max_sources: int = 10
    knowledge_base: KnowledgeBase | None = None


@dataclass
class ResearchTask:
    """A research task with input and output tracking."""

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str = ""
    context: str = ""
    status: str = "pending"  # pending | running | completed | failed
    sub_queries: list[str] = field(default_factory=list)
    sources: list[SearchResult] = field(default_factory=list)
    synthesis: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResearchResult:
    """Final research output."""

    task_id: str
    query: str
    synthesis: str
    sources: list[SearchResult]
    sub_queries_used: list[str]
    iterations: int
    duration_seconds: float


class ResearchAgent:
    """Multi-step research agent for web intelligence tasks.

    Workflow:
    1. Analyze query → decompose into sub-queries
    2. Search each sub-query → collect sources
    3. Synthesize findings → return structured result

    Usage:
        >>> agent = ResearchAgent(kb)
        >>> result = await agent.research("What is the best Python web framework in 2026?")
        >>> print(result.synthesis)
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        config: ResearchConfig | None = None,
    ) -> None:
        self._kb = knowledge_base or KnowledgeBase()
        self._config = config or ResearchConfig(knowledge_base=self._kb)
        self._tasks: dict[str, ResearchTask] = {}

    # ── Main research flow ───────────────────────────────────────────────

    async def research(
        self,
        query: str,
        context: str = "",
        max_sources: int | None = None,
    ) -> ResearchResult:
        """Execute a multi-step research task.

        Args:
            query: The research question or topic.
            context: Optional additional context for the query.
            max_sources: Override the default max sources limit.

        Returns:
            ResearchResult with synthesis and citations.
        """
        started = datetime.now(timezone.utc)
        task = ResearchTask(query=query, context=context, status="running")
        self._tasks[task.task_id] = task

        max_src = max_sources or self._config.max_sources

        try:
            # Step 1: Generate sub-queries
            sub_queries = await self._decompose_query(query, context)
            task.sub_queries = sub_queries
            logger.info("Research [%s]: %d sub-queries generated", task.task_id, len(sub_queries))

            # Step 2: Search each sub-query
            all_sources: list[SearchResult] = []
            seen_urls: set[str] = set()

            for sq in sub_queries[:self._config.max_iterations]:
                try:
                    results = await self._kb.search(sq, num_results=5)
                    for r in results:
                        if r.url not in seen_urls and len(all_sources) < max_src:
                            seen_urls.add(r.url)
                            all_sources.append(r)
                except Exception as e:
                    logger.warning("Sub-query search failed [%s]: %s", sq, e)

            task.sources = all_sources

            # Step 3: Synthesize findings
            synthesis = await self._synthesize(query, all_sources, context)
            task.synthesis = synthesis
            task.status = "completed"

        except Exception as e:
            task.status = "failed"
            logger.error("Research [%s] failed: %s", task.task_id, e)
            raise

        duration = (datetime.now(timezone.utc) - started).total_seconds()

        return ResearchResult(
            task_id=task.task_id,
            query=query,
            synthesis=task.synthesis,
            sources=task.sources,
            sub_queries_used=task.sub_queries,
            iterations=len(task.sub_queries),
            duration_seconds=duration,
        )

    # ── Internal methods ───────────────────────────────────────────────────

    async def _decompose_query(
        self, query: str, context: str = ""
    ) -> list[str]:
        """Decompose a research query into targeted sub-queries.

        Uses simple heuristics; in production, this would use an LLM.
        """
        sub_queries = [query]

        # Heuristic: add contextual variations
        if context:
            sub_queries.append(f"{query} {context}")

        # Heuristic: add "how to" and "best practices" variants
        if not query.lower().startswith("how"):
            sub_queries.append(f"How to {query}")
        if "best" not in query.lower():
            sub_queries.append(f"Best {query}")

        # Heuristic: add "vs" comparison if contains comparison keywords
        comparison_keywords = ["vs", "versus", "compare", "comparison", "or", "between"]
        if any(kw in query.lower() for kw in comparison_keywords):
            sub_queries.append(f"{query} comparison 2026")

        return sub_queries[:self._config.max_iterations]

    async def _synthesize(
        self,
        query: str,
        sources: list[SearchResult],
        context: str = "",
    ) -> str:
        """Synthesize research findings into a coherent summary.

        In production, this would use an LLM for summarization.
        For now, produces a structured markdown summary.
        """
        if not sources:
            return f"No relevant sources found for: {query}"

        lines = [
            f"# Research: {query}",
            "",
            f"*{len(sources)} sources analyzed*",
            "",
            "## Key Findings",
            "",
        ]

        for i, src in enumerate(sources[:5], 1):
            lines.append(f"{i}. **{src.title}**")
            lines.append(f"   {src.snippet}")
            if src.url:
                lines.append(f"   Source: [{src.url}]({src.url})")
            lines.append("")

        if len(sources) > 5:
            lines.append(f"*...and {len(sources) - 5} more sources*")

        lines.append("## Summary")
        lines.append("")
        lines.append("Based on the collected sources, the key insights are synthesized above. "
                      "For production use, configure an LLM backend for deeper synthesis.")

        return "\n".join(lines)

    # ── Task management ──────────────────────────────────────────────────

    def get_task(self, task_id: str) -> ResearchTask | None:
        """Get a research task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[ResearchTask]:
        """List all research tasks."""
        return list(self._tasks.values())