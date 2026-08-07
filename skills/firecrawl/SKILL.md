---
name: firecrawl
description: Web scraping, crawling, search, site mapping, structured extraction, and document parsing skill. Powered by Firecrawl API with local fallback capabilities.
version: 1.0.0
category: research
when_to_use: User asks to scrape, crawl, search, map, or extract structured data from websites, or parse web documents (HTML, PDF, Markdown) into clean content.
---

# Firecrawl Skill

Firecrawl is a comprehensive web intelligence skill that enables SKPL Agent to
interact with web content through six core capabilities:

1. **Scrape** -- Fetch and extract content from a single URL
2. **Crawl** -- Recursively crawl a website with configurable depth and scope
3. **Search** -- Perform web searches via integrated search engines
4. **Map** -- Discover all URLs on a website via sitemap or link crawling
5. **Extract** -- Extract structured data from web pages using CSS selectors or LLM
6. **Parse** -- Parse content into structured formats (HTML, PDF, Markdown, JSON-LD)

## Dependencies

- **Python**: `aiohttp>=3.9`, `beautifulsoup4>=4.12`, `lxml>=4.9`, `markdownify>=0.12`
- **Optional**: `pdfplumber>=0.10` (for PDF parsing), `httpx>=0.27` (for API client)

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl API key | `""` |
| `FIRECRAWL_API_ENDPOINT` | Firecrawl API endpoint | `https://api.firecrawl.dev` |
| `SKPL_WEB_CRAWLER_CONCURRENCY` | Max concurrent crawls | `3` |
| `SKPL_WEB_WEB_RATE_LIMIT_PER_MINUTE` | Rate limit per minute | `30` |

### API Key

To use the Firecrawl API (required for LLM extraction and advanced search), obtain
an API key from [https://firecrawl.dev](https://firecrawl.dev) and set it as an
environment variable or in the configuration.

Without an API key, the skill operates in local-only mode using:
- Direct HTTP scraping via `aiohttp`
- BeautifulSoup-based HTML parsing
- Google SERP scraping (without API)

## MCP Configuration

This skill exposes its tools via MCP (Model Context Protocol). See `mcp_config.json`
for the complete MCP server configuration.

## Usage Examples

### Scrape a Single Page

```python
from skpl_agent.skills.firecrawl.tools.scrape import Scraper
from skpl_agent.app._service.firecrawl_service import FirecrawlConfig

config = FirecrawlConfig()
scraper = Scraper(config)
result = await scraper.scrape("https://example.com")
print(result.title, result.content_markdown)
```

### Crawl a Website

```python
from skpl_agent.skills.firecrawl.tools.crawl import Crawler

crawler = Crawler(config)
result = await crawler.crawl("https://docs.example.com", max_depth=2, max_pages=50)
for page in result.results:
    print(page.url, page.title)
```

### Search the Web

```python
from skpl_agent.skills.firecrawl.tools.search import Searcher

searcher = Searcher(config)
results = await searcher.search("machine learning tutorials", num_results=10)
for r in results.results:
    print(r.title, r.url)
```

### Map a Site

```python
from skpl_agent.skills.firecrawl.tools.map import SiteMapper

mapper = SiteMapper(config)
result = await mapper.map("https://example.com", max_pages=500)
for page in result.pages:
    print(page["url"])
```

### Extract Structured Data

```python
from skpl_agent.skills.firecrawl.tools.extract import Extractor

extractor = Extractor(config)
result = await extractor.extract(
    "https://books.toscrape.com",
    schema={
        "title": "h1",
        "price": ".price_color",
        "availability": {"selector": ".availability", "attribute": "class"},
    },
)
print(result.data)
```

### Parse Content

```python
from skpl_agent.skills.firecrawl.tools.parse import Parser

parser = Parser()
result = parser.parse_html(html_content)
print(result.markdown)
print(result.statistics)
```

## Security

- **SSRF Protection**: All URLs are validated against internal network ranges
- **Rate Limiting**: Per-domain rate limiting with configurable thresholds
- **Robots.txt Compliance**: Optional respect for robots.txt directives
- **Content Size Limits**: Configurable maximum content size (default 50MB)

## Architecture

```
skills/firecrawl/
  SKILL.md              # This file
  mcp_config.json       # MCP server configuration
  firecrawl_client.py   # HTTP client for Firecrawl API
  tools/
    __init__.py         # Package exports
    scrape.py           # Single-page scraper
    crawl.py            # Recursive crawler
    search.py           # Web search engine
    map.py              # Site map generator
    extract.py          # Structured data extractor
    parse.py            # Content parser
```