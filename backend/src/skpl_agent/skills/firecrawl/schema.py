"""Firecrawl Pydantic schemas — request/response data models.

Defines type-safe data models for all Firecrawl API operations.
These are used by the client for validation and serialization,
and by the service layer for API contract enforcement.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ScrapeFormat(str, Enum):
    """Output format for scraped content."""

    MARKDOWN = "markdown"
    HTML = "html"
    RAW_HTML = "rawHtml"
    TEXT = "text"
    SCREENSHOT = "screenshot"


class CrawlStatus(str, Enum):
    """Crawl job status."""

    SCRAPING = "scraping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SearchSource(str, Enum):
    """Search engine source."""

    WEB = "web"
    NEWS = "news"
    IMAGES = "images"


class ExtractMode(str, Enum):
    """Extraction mode."""

    LLM = "llm"
    CSS = "css"
    XPATH = "xpath"


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------


class ScrapeRequest(BaseModel):
    """Request to scrape a single URL."""

    url: str = Field(..., min_length=1, max_length=2048)
    formats: list[ScrapeFormat] = Field(default=[ScrapeFormat.MARKDOWN])
    only_main_content: bool = True
    include_tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    wait_for: int = Field(default=0, ge=0, le=30000)
    timeout: int = Field(default=30000, ge=1000, le=120000)
    mobile: bool = False
    country: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    extract: dict[str, Any] | None = None


class ScrapeMetadata(BaseModel):
    """Metadata for a scraped page."""

    title: str | None = None
    description: str | None = None
    language: str | None = None
    source_url: str | None = None
    status_code: int = 200
    content_type: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    og_url: str | None = None
    og_site_name: str | None = None
    twitter_card: str | None = None
    favicon: str | None = None


class ScrapeResponse(BaseModel):
    """Response from a scrape operation."""

    success: bool = True
    data: dict[str, Any] | None = None
    markdown: str | None = None
    html: str | None = None
    raw_html: str | None = None
    text: str | None = None
    screenshot: str | None = None
    links: list[str] = Field(default_factory=list)
    metadata: ScrapeMetadata | None = None
    warning: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------


class CrawlRequest(BaseModel):
    """Request to crawl a website."""

    url: str = Field(..., min_length=1, max_length=2048)
    max_depth: int = Field(default=2, ge=1, le=10)
    limit: int = Field(default=100, ge=1, le=10000)
    allow_backward_links: bool = False
    allow_external_links: bool = False
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=list)
    formats: list[ScrapeFormat] = Field(default=[ScrapeFormat.MARKDOWN])
    only_main_content: bool = True
    headers: dict[str, str] = Field(default_factory=dict)
    timeout: int = Field(default=120000, ge=1000, le=600000)
    webhook_url: str | None = None
    idempotency_key: str | None = None


class CrawlJobStatus(BaseModel):
    """Status of a crawl job."""

    id: str
    url: str
    status: CrawlStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    total: int = 0
    completed: int = 0
    credits_used: int = 0
    expires_at: datetime | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    next: str | None = None
    error: str | None = None


class CrawlResponse(BaseModel):
    """Response from initiating a crawl."""

    success: bool = True
    id: str | None = None
    url: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request to search the web."""

    query: str = Field(..., min_length=1, max_length=500)
    source: SearchSource = SearchSource.WEB
    limit: int = Field(default=10, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    lang: str | None = None
    country: str | None = None
    tbs: str | None = None
    timeout: int = Field(default=60000, ge=1000, le=120000)
    scrape_options: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A single search result."""

    url: str
    title: str
    description: str | None = None
    position: int = 0
    content: str | None = None
    markdown: str | None = None


class SearchResponse(BaseModel):
    """Response from a web search."""

    success: bool = True
    query: str
    total_results: int = 0
    results: list[SearchResult] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------


class MapRequest(BaseModel):
    """Request to discover URLs on a site."""

    url: str = Field(..., min_length=1, max_length=2048)
    search: str | None = None
    sitemap_only: bool = False
    include_subdomains: bool = False
    limit: int = Field(default=5000, ge=1, le=50000)
    ignore_sitemap: bool = False
    timeout: int = Field(default=60000, ge=1000, le=300000)


class MapResponse(BaseModel):
    """Response from a site map operation."""

    success: bool = True
    links: list[str] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


class ExtractRequest(BaseModel):
    """Request to extract structured data from URLs."""

    urls: list[str] = Field(..., min_length=1, max_length=100)
    prompt: str = Field(..., min_length=1, max_length=10000)
    mode: ExtractMode = ExtractMode.LLM
    schema: dict[str, Any] | None = None
    system_prompt: str | None = None
    allow_external_links: bool = False
    enable_web_search: bool = False
    timeout: int = Field(default=300000, ge=1000, le=600000)
    origin: str | None = None


class ExtractResponse(BaseModel):
    """Response from an extract operation."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    warning: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


class ParseRequest(BaseModel):
    """Request to parse raw content."""

    content: str = Field(..., min_length=1)
    format: str = "markdown"
    extract: dict[str, Any] | None = None


class ParseResponse(BaseModel):
    """Response from a parse operation."""

    success: bool = True
    markdown: str | None = None
    text: str | None = None
    html: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class FirecrawlError(BaseModel):
    """Standardized error response from Firecrawl API."""

    success: bool = False
    error: str
    message: str | None = None
    status_code: int | None = None
    retry_after: int | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class FirecrawlHealthResponse(BaseModel):
    """Health check response from Firecrawl API."""

    status: str = "ok"
    version: str | None = None
    uptime: float | None = None


__all__ = [
    # Enums
    "ScrapeFormat",
    "CrawlStatus",
    "SearchSource",
    "ExtractMode",
    # Scrape
    "ScrapeRequest",
    "ScrapeMetadata",
    "ScrapeResponse",
    # Crawl
    "CrawlRequest",
    "CrawlJobStatus",
    "CrawlResponse",
    # Search
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    # Map
    "MapRequest",
    "MapResponse",
    # Extract
    "ExtractRequest",
    "ExtractResponse",
    # Parse
    "ParseRequest",
    "ParseResponse",
    # Error
    "FirecrawlError",
    "FirecrawlHealthResponse",
]