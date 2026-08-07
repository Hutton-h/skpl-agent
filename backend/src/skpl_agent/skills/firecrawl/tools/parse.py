"""Firecrawl parse — content parsing and format conversion.

Handles parsing of various content types:
- HTML to structured content
- PDF text extraction
- Markdown conversion
- JSON-LD extraction
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of content parsing."""

    content_type: str = ""
    text: str = ""
    markdown: str = ""
    html: str = ""
    json_ld: list[dict[str, Any]] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class Parser:
    """Parses web content into structured formats.

    Handles:
    - HTML to Markdown conversion
    - JSON-LD structured data extraction
    - Table extraction
    - Content statistics (word count, reading time, etc.)
    - PDF text extraction (requires pdfplumber)

    Usage:
        >>> parser = Parser()
        >>> result = parser.parse_html(html_content)
        >>> print(result.markdown)
    """

    # ── HTML Parsing ─────────────────────────────────────────────────────

    def parse_html(self, html: str, url: str = "") -> ParseResult:
        """Parse HTML content into structured formats.

        Args:
            html: Raw HTML content.
            url: Source URL for relative link resolution.

        Returns:
            ParseResult with extracted content.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")

            # Remove unwanted elements
            for tag in soup.find_all(["script", "style", "noscript", "iframe"]):
                tag.decompose()

            # Extract JSON-LD
            json_ld = self._extract_json_ld(soup)

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Convert to markdown
            markdown = self._html_to_markdown(html)

            # Extract tables
            tables = self._extract_tables(soup)

            # Statistics
            stats = self._compute_stats(text)

            return ParseResult(
                content_type="text/html",
                text=text,
                markdown=markdown,
                html=html,
                json_ld=json_ld,
                tables=tables,
                statistics=stats,
            )

        except Exception as e:
            logger.error("HTML parse error: %s", e)
            return ParseResult(content_type="text/html", error=str(e))

    def parse_text(self, text: str) -> ParseResult:
        """Parse plain text content."""
        stats = self._compute_stats(text)
        return ParseResult(
            content_type="text/plain",
            text=text,
            markdown=text,
            statistics=stats,
        )

    def parse_markdown(self, markdown: str) -> ParseResult:
        """Parse Markdown content."""
        try:
            import markdown as md_lib
            html = md_lib.markdown(markdown)
            text = re.sub(r"<[^>]+>", "", html)
            stats = self._compute_stats(text)

            return ParseResult(
                content_type="text/markdown",
                text=text,
                markdown=markdown,
                html=html,
                statistics=stats,
            )
        except Exception as e:
            logger.error("Markdown parse error: %s", e)
            return ParseResult(content_type="text/markdown", error=str(e))

    def parse_pdf(self, pdf_bytes: bytes) -> ParseResult:
        """Parse PDF content.

        Requires pdfplumber to be installed.
        """
        try:
            import io
            import pdfplumber

            text_parts: list[str] = []
            tables: list[list[list[str]]] = []

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            tables.append(table)

            text = "\n\n".join(text_parts)
            stats = self._compute_stats(text)

            return ParseResult(
                content_type="application/pdf",
                text=text,
                markdown=text,
                tables=tables,
                statistics=stats,
            )

        except ImportError:
            return ParseResult(
                content_type="application/pdf",
                error="pdfplumber is required for PDF parsing",
            )
        except Exception as e:
            logger.error("PDF parse error: %s", e)
            return ParseResult(content_type="application/pdf", error=str(e))

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_json_ld(soup) -> list[dict[str, Any]]:
        """Extract JSON-LD structured data from HTML."""
        json_ld_list: list[dict[str, Any]] = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    json_ld_list.extend(data)
                else:
                    json_ld_list.append(data)
            except (json.JSONDecodeError, TypeError):
                pass

        return json_ld_list

    @staticmethod
    def _extract_tables(soup) -> list[list[list[str]]]:
        """Extract HTML tables."""
        tables: list[list[list[str]]] = []

        for table in soup.find_all("table"):
            rows: list[list[str]] = []
            for tr in table.find_all("tr"):
                cells: list[str] = []
                for cell in tr.find_all(["td", "th"]):
                    cells.append(cell.get_text(strip=True))
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)

        return tables

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """Convert HTML to Markdown."""
        try:
            from markdownify import markdownify
            return markdownify(
                html,
                heading_style="ATX",
                strip=["script", "style", "img"],
            )
        except ImportError:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            return soup.get_text(separator="\n\n", strip=True)

    @staticmethod
    def _compute_stats(text: str) -> dict[str, Any]:
        """Compute content statistics."""
        words = text.split()
        char_count = len(text)
        word_count = len(words)
        line_count = text.count("\n") + 1
        sentence_count = len(re.findall(r"[.!?]+", text)) or 1

        # Average reading speed: 200 words per minute
        reading_time_minutes = word_count / 200

        return {
            "char_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "sentence_count": sentence_count,
            "reading_time_seconds": round(reading_time_minutes * 60, 1),
            "reading_time_minutes": round(reading_time_minutes, 1),
        }