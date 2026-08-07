"""Request/response schemas for web intelligence endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Search ───────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    engine: str | None = Field(None, description="Search engine: duckduckgo, perplexica, llm")
    num_results: int = Field(5, ge=1, le=20, description="Number of results")


class SearchResultSchema(BaseModel):
    title: str
    url: str
    snippet: str
    source: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultSchema]
    total: int


# ── Knowledge Retrieval ──────────────────────────────────────────────────

class KnowledgeRequest(BaseModel):
    instruction: str = Field(..., min_length=1, description="Task instruction")
    search_query: str | None = Field(None, description="Pre-formulated search query")
    engine: str | None = None


class KnowledgeResponse(BaseModel):
    query: str
    results: list[SearchResultSchema]


# ── Research ─────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Research question")
    context: str = Field("", description="Additional context")
    max_sources: int | None = Field(None, ge=1, le=50, description="Max sources")


class ResearchResponse(BaseModel):
    task_id: str
    query: str
    synthesis: str
    sources: list[SearchResultSchema]
    sub_queries_used: list[str]
    iterations: int
    duration_seconds: float


class ResearchStatusResponse(BaseModel):
    task_id: str
    query: str
    status: str
    sub_queries: list[str]
    sources_count: int
    synthesis: str


class ResearchListItem(BaseModel):
    task_id: str
    query: str
    status: str
    sources_count: int