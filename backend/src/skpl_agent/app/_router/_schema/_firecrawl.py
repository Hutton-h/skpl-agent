"""Pydantic schemas for Firecrawl web scraping and crawling API.

Provides request/response models for all six Firecrawl operations:
- Scrape: Single page scraping
- Crawl: Recursive website crawling
- Search: Web search
- Map: Site URL discovery
- Extract: Structured data extraction
- Parse: Content parsing

All models include field validation (URL format, value ranges, etc.)
and are used by the Firecrawl router and service layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------


class ScrapeRequest(BaseModel):
    """Request to scrape a single URL."""

    url: str = Field(
        description="The URL to scrape. Must be a valid HTTP/HTTPS URL.",
        min_length=1,
        max_length=4096,
    )
    formats: list[str] = Field(
        default=["markdown"],
        description="Output formats to include: markdown, html, text.",
    )
    only_main_content: bool = Field(
        default=True,
        description="Extract only the main content, excluding headers, footers, nav, etc.",
    )
    wait_for: int = Field(
        default=0,
        ge=0,
        le=30000,
        description="Wait time in milliseconds before scraping (for JS-rendered pages).",
    )
    include_tags: list[str] = Field(
        default_factory=list,
        description="HTML tags to include in the extracted content.",
    )
    exclude_tags: list[str] = Field(
        default_factory=list,
        description="HTML tags to exclude from the extracted content.",
    )

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Validate that URL uses HTTP or HTTPS."""
        v_lower = v.lower()
        if not v_lower.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, v: list[str]) -> list[str]:
        """Validate output formats."""
        allowed = {"markdown", "html", "text"}
        for fmt in v:
            if fmt not in allowed:
                raise ValueError(f"Invalid format '{fmt}'. Allowed: {allowed}")
        return v


class ScrapeResponse(BaseModel):
    """Response from a scrape operation."""

    url: str = Field(description="The scraped URL.")
    title: str = Field(default="", description="Page title.")
    description: str = Field(default="", description="Meta description.")
    content_markdown: str = Field(default="", description="Content in Markdown format.")
    content_html: str = Field(default="", description="Content in HTML format.")
    content_text: str = Field(default="", description="Content in plain text format.")
    links: list[str] = Field(default_factory=list, description="Discovered links.")
    images: list[str] = Field(default_factory=list, description="Discovered images.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Page metadata.")
    status_code: int = Field(default=0, description="HTTP status code.")
    error: str = Field(default="", description="Error message if scrape failed.")
    duration_ms: float = Field(default=0.0, description="Request duration in milliseconds.")


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------


class CrawlRequest(BaseModel):
    """Request to crawl a website recursively."""

    url: str = Field(
        description="Starting URL for the crawl.",
        min_length=1,
        max_length=4096,
    )
    max_depth: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum crawl depth (1-10).",
    )
    max_pages: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of pages to crawl (1-500).",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="URL patterns to include (regex).",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="URL patterns to exclude (regex).",
    )
    scrape_formats: list[str] = Field(
        default=["markdown"],
        description="Output formats for each scraped page.",
    )

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Validate that URL uses HTTP or HTTPS."""
        v_lower = v.lower()
        if not v_lower.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class CrawlPageResult(BaseModel):
    """A single page result within a crawl."""

    url: str = Field(description="Page URL.")
    title: str = Field(default="", description="Page title.")
    content_markdown: str = Field(default="", description="Content in Markdown format.")
    content_html: str = Field(default="", description="Content in HTML format.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Page metadata.")


class CrawlResponse(BaseModel):
    """Response from a crawl operation."""

    job_id: str = Field(default="", description="Crawl job identifier.")
    url: str = Field(description="Starting URL.")
    status: str = Field(
        default="pending",
        description="Crawl status: pending, running, completed, failed.",
    )
    pages: list[CrawlPageResult] = Field(
        default_factory=list,
        description="Scraped pages.",
    )
    total_pages: int = Field(default=0, description="Total pages scraped.")
    pages_failed: int = Field(default=0, description="Number of pages that failed.")
    credits_used: int = Field(default=0, description="API credits consumed.")
    error: str = Field(default="", description="Error message if crawl failed.")
    duration_ms: float = Field(default=0.0, description="Crawl duration in milliseconds.")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request to perform a web search."""

    query: str = Field(
        description="Search query string.",
        min_length=1,
        max_length=2048,
    )
    engine: str = Field(
        default="google",
        description="Search engine to use: google or bing.",
    )
    num_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100).",
    )
    language: str = Field(
        default="en",
        description="Language code for results (e.g., 'en', 'zh-CN').",
    )
    country: str = Field(
        default="",
        description="Country code for localized results (e.g., 'us', 'cn').",
    )

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        """Validate search engine."""
        allowed = {"google", "bing"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid engine '{v}'. Allowed: {allowed}")
        return v.lower()


class SearchResultItem(BaseModel):
    """A single search result."""

    title: str = Field(description="Result title.")
    url: str = Field(description="Result URL.")
    snippet: str = Field(default="", description="Result snippet/description.")
    position: int = Field(default=0, description="Position in search results.")
    domain: str = Field(default="", description="Domain of the result URL.")


class SearchResponse(BaseModel):
    """Response from a search operation."""

    query: str = Field(description="The search query.")
    engine: str = Field(default="google", description="Search engine used.")
    results: list[SearchResultItem] = Field(
        default_factory=list,
        description="Search results.",
    )
    total_results: int = Field(default=0, description="Total number of results found.")
    error: str = Field(default="", description="Error message if search failed.")
    duration_ms: float = Field(default=0.0, description="Search duration in milliseconds.")


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------


class MapRequest(BaseModel):
    """Request to discover all URLs on a website."""

    url: str = Field(
        description="Website URL to map.",
        min_length=1,
        max_length=4096,
    )
    max_pages: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Maximum number of URLs to discover (1-5000).",
    )
    include_subdomains: bool = Field(
        default=False,
        description="Whether to include subdomain URLs.",
    )

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Validate that URL uses HTTP or HTTPS."""
        v_lower = v.lower()
        if not v_lower.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class MapPageEntry(BaseModel):
    """A page entry in the site map."""

    url: str = Field(description="Page URL.")
    title: str = Field(default="", description="Page title.")
    type: str = Field(default="page", description="Entry type: page or sitemap.")
    description: str = Field(default="", description="Page description.")
    last_modified: str | None = Field(default=None, description="Last modified date.")
    change_frequency: str | None = Field(default=None, description="Change frequency.")
    priority: float | None = Field(default=None, description="Page priority (0.0-1.0).")


class MapResponse(BaseModel):
    """Response from a site map operation."""

    url: str = Field(description="The mapped website URL.")
    status: str = Field(default="pending", description="Map status: pending, running, completed, failed.")
    pages: list[MapPageEntry] = Field(
        default_factory=list,
        description="Discovered pages.",
    )
    total_pages: int = Field(default=0, description="Total pages discovered.")
    error: str = Field(default="", description="Error message if mapping failed.")
    duration_ms: float = Field(default=0.0, description="Mapping duration in milliseconds.")


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


class ExtractRequest(BaseModel):
    """Request to extract structured data from a URL."""

    url: str = Field(
        description="URL to extract data from.",
        min_length=1,
        max_length=4096,
    )
    schema: dict[str, Any] = Field(
        description="Extraction schema. Keys are field names, values are CSS selectors or type descriptions.",
    )
    use_llm: bool = Field(
        default=False,
        description="Whether to use LLM for extraction (requires API key).",
    )
    llm_prompt: str = Field(
        default="",
        description="Additional prompt for LLM extraction.",
        max_length=4096,
    )

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Validate that URL uses HTTP or HTTPS."""
        v_lower = v.lower()
        if not v_lower.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ExtractResponse(BaseModel):
    """Response from an extract operation."""

    url: str = Field(description="The extracted URL.")
    data: dict[str, Any] = Field(default_factory=dict, description="Extracted structured data.")
    error: str = Field(default="", description="Error message if extraction failed.")
    duration_ms: float = Field(default=0.0, description="Extraction duration in milliseconds.")


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


class ParseRequest(BaseModel):
    """Request to parse content into structured formats."""

    content: str = Field(
        description="Raw content to parse.",
        min_length=1,
    )
    content_type: str = Field(
        default="html",
        description="Type of content: html, text, markdown, pdf.",
    )
    url: str = Field(
        default="",
        description="Source URL for relative link resolution.",
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        allowed = {"html", "text", "markdown", "pdf"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid content type '{v}'. Allowed: {allowed}")
        return v.lower()


class ParseResponse(BaseModel):
    """Response from a parse operation."""

    content_type: str = Field(default="", description="Parsed content type.")
    text: str = Field(default="", description="Plain text content.")
    markdown: str = Field(default="", description="Markdown content.")
    html: str = Field(default="", description="HTML content.")
    json_ld: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted JSON-LD structured data.",
    )
    tables: list[list[list[str]]] = Field(
        default_factory=list,
        description="Extracted tables.",
    )
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Content statistics (word count, reading time, etc.).",
    )
    error: str = Field(default="", description="Error message if parsing failed.")