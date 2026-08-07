"""Unit tests for web_intelligence_service.py — Web research service.

Tests cover:
- WebIntelligenceService initialization
- search, retrieve_knowledge, start_research
- get_research_status, list_research_tasks
- get_available_engines
- Error paths: missing tasks, mock external dependencies
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_search_result() -> MagicMock:
    """Create a mock SearchResult."""
    mock = MagicMock()
    mock.title = "Test Result"
    mock.url = "https://example.com"
    mock.snippet = "A test snippet"
    mock.source = "duckduckgo"
    return mock


@pytest.fixture
def mock_research_result() -> MagicMock:
    """Create a mock ResearchResult."""
    mock = MagicMock()
    mock.task_id = "task-123"
    mock.query = "test query"
    mock.synthesis = "Research synthesis"
    mock.sources = []
    mock.sub_queries_used = ["sub1", "sub2"]
    mock.iterations = 3
    mock.duration_seconds = 5.0
    return mock


@pytest.fixture
def mock_research_task() -> MagicMock:
    """Create a mock ResearchTask."""
    mock = MagicMock()
    mock.task_id = "task-123"
    mock.query = "test query"
    mock.status = "completed"
    mock.sub_queries = ["sub1", "sub2"]
    mock.sources = []
    mock.synthesis = "Research synthesis"
    return mock


# ── Service Init Tests ─────────────────────────────────────────────────────


class TestWebIntelligenceServiceInit:
    """Tests for WebIntelligenceService initialization."""

    def test_service_initializes(self) -> None:
        """WebIntelligenceService can be instantiated."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )
            svc = WebIntelligenceService()
            assert svc is not None
            assert svc._kb is not None
            assert svc._research_agent is not None


# ── Search Tests ───────────────────────────────────────────────────────────


class TestSearch:
    """Tests for search method."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_search_result: MagicMock) -> None:
        """search returns formatted search results."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb.search = AsyncMock(return_value=[mock_search_result])
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            results = await svc.search("test query", num_results=5)
            assert len(results) == 1
            assert results[0]["title"] == "Test Result"
            assert results[0]["url"] == "https://example.com"
            assert results[0]["snippet"] == "A test snippet"
            assert results[0]["source"] == "duckduckgo"

    @pytest.mark.asyncio
    async def test_search_with_engine(self) -> None:
        """search passes engine parameter through."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb.search = AsyncMock(return_value=[])
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            await svc.search("query", engine="perplexica")
            mock_kb.search.assert_called_once_with(
                "query", engine="perplexica", num_results=5
            )

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """search returns empty list when no results."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb.search = AsyncMock(return_value=[])
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            results = await svc.search("no results")
            assert results == []


# ── Retrieve Knowledge Tests ───────────────────────────────────────────────


class TestRetrieveKnowledge:
    """Tests for retrieve_knowledge method."""

    @pytest.mark.asyncio
    async def test_retrieve_knowledge_returns_dict(self, mock_search_result: MagicMock) -> None:
        """retrieve_knowledge returns query and results."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb.retrieve_knowledge = AsyncMock(
                return_value=("search query", [mock_search_result])
            )
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            result = await svc.retrieve_knowledge("How to write tests?")
            assert result["query"] == "search query"
            assert len(result["results"]) == 1
            assert result["results"][0]["title"] == "Test Result"

    @pytest.mark.asyncio
    async def test_retrieve_knowledge_with_search_query(self) -> None:
        """retrieve_knowledge accepts optional search_query."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb.retrieve_knowledge = AsyncMock(
                return_value=("custom query", [])
            )
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            await svc.retrieve_knowledge(
                "instruction", search_query="custom", engine="duckduckgo"
            )
            mock_kb.retrieve_knowledge.assert_called_once_with(
                "instruction", search_query="custom", search_engine="duckduckgo"
            )


# ── Start Research Tests ───────────────────────────────────────────────────


class TestStartResearch:
    """Tests for start_research method."""

    @pytest.mark.asyncio
    async def test_start_research_returns_dict(
        self, mock_research_result: MagicMock
    ) -> None:
        """start_research returns formatted research result."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_ra = MagicMock()
            mock_ra.research = AsyncMock(return_value=mock_research_result)
            mock_ra_cls.return_value = mock_ra

            svc = WebIntelligenceService()
            svc._research_agent = mock_ra

            result = await svc.start_research("test query", context="context")
            assert result["task_id"] == "task-123"
            assert result["query"] == "test query"
            assert result["synthesis"] == "Research synthesis"
            assert result["sub_queries_used"] == ["sub1", "sub2"]
            assert result["iterations"] == 3
            assert result["duration_seconds"] == 5.0

    @pytest.mark.asyncio
    async def test_start_research_with_max_sources(
        self, mock_research_result: MagicMock
    ) -> None:
        """start_research passes max_sources to research agent."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_ra = MagicMock()
            mock_ra.research = AsyncMock(return_value=mock_research_result)
            mock_ra_cls.return_value = mock_ra

            svc = WebIntelligenceService()
            svc._research_agent = mock_ra

            await svc.start_research("query", max_sources=10)
            mock_ra.research.assert_called_once_with(
                "query", context="", max_sources=10
            )


# ── Get Research Status Tests ──────────────────────────────────────────────


class TestGetResearchStatus:
    """Tests for get_research_status method."""

    @pytest.mark.asyncio
    async def test_get_research_status_existing(self, mock_research_task: MagicMock) -> None:
        """get_research_status returns task info for existing task."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_ra = MagicMock()
            mock_ra.get_task = MagicMock(return_value=mock_research_task)
            mock_ra_cls.return_value = mock_ra

            svc = WebIntelligenceService()
            svc._research_agent = mock_ra

            status = await svc.get_research_status("task-123")
            assert status is not None
            assert status["task_id"] == "task-123"
            assert status["status"] == "completed"
            assert status["query"] == "test query"

    @pytest.mark.asyncio
    async def test_get_research_status_nonexistent(self) -> None:
        """get_research_status returns None for unknown task."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_ra = MagicMock()
            mock_ra.get_task = MagicMock(return_value=None)
            mock_ra_cls.return_value = mock_ra

            svc = WebIntelligenceService()
            svc._research_agent = mock_ra

            status = await svc.get_research_status("nonexistent")
            assert status is None


# ── List Research Tasks Tests ──────────────────────────────────────────────


class TestListResearchTasks:
    """Tests for list_research_tasks method."""

    @pytest.mark.asyncio
    async def test_list_research_tasks_empty(self) -> None:
        """list_research_tasks returns empty list when no tasks."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_ra = MagicMock()
            mock_ra.list_tasks = MagicMock(return_value=[])
            mock_ra_cls.return_value = mock_ra

            svc = WebIntelligenceService()
            svc._research_agent = mock_ra

            tasks = await svc.list_research_tasks()
            assert tasks == []

    @pytest.mark.asyncio
    async def test_list_research_tasks_with_tasks(self) -> None:
        """list_research_tasks returns formatted task list."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent") as mock_ra_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_task = MagicMock()
            mock_task.task_id = "t1"
            mock_task.query = "q1"
            mock_task.status = "running"
            mock_task.sources = [MagicMock()]

            mock_ra = MagicMock()
            mock_ra.list_tasks = MagicMock(return_value=[mock_task])
            mock_ra_cls.return_value = mock_ra

            svc = WebIntelligenceService()
            svc._research_agent = mock_ra

            tasks = await svc.list_research_tasks()
            assert len(tasks) == 1
            assert tasks[0]["task_id"] == "t1"
            assert tasks[0]["status"] == "running"
            assert tasks[0]["sources_count"] == 1


# ── Get Available Engines Tests ────────────────────────────────────────────


class TestGetAvailableEngines:
    """Tests for get_available_engines method."""

    @pytest.mark.asyncio
    async def test_get_available_engines_returns_list(self) -> None:
        """get_available_engines returns a list of engine names."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb._engines = {"duckduckgo": MagicMock(), "perplexica": MagicMock()}
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            engines = await svc.get_available_engines()
            assert isinstance(engines, list)
            assert "duckduckgo" in engines
            assert "perplexica" in engines

    @pytest.mark.asyncio
    async def test_get_available_engines_defaults(self) -> None:
        """get_available_engines returns defaults when _engines is empty."""
        with patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBase") as mock_kb_cls, \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchAgent"), \
             patch("skpl_agent.app._service.web_intelligence_service.KnowledgeBaseConfig"), \
             patch("skpl_agent.app._service.web_intelligence_service.ResearchConfig"):
            from skpl_agent.app._service.web_intelligence_service import (
                WebIntelligenceService,
            )

            mock_kb = MagicMock()
            mock_kb._engines = {}
            mock_kb_cls.return_value = mock_kb

            svc = WebIntelligenceService()
            svc._kb = mock_kb

            engines = await svc.get_available_engines()
            assert engines == ["duckduckgo", "perplexica", "llm"]