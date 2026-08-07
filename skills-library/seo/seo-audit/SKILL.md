---
name: seo-audit
description: On-page SEO audit workflow. Scrapes the target website, checks title/meta/headings/performance/mobile/internal links, produces a severity-graded issue list with concrete fix recommendations in a report file.
version: 1.0.0
category: seo
when_to_use: User asks to audit a website's SEO, find on-page SEO problems, or wants prioritized SEO fix recommendations for a site.
---

# SEO Audit Skill — 网站 SEO 审计

## Goal
Audit a live website and deliver a severity-graded issue list with fixes as a downloadable report (md/docx) plus an optional issue-tracking xlsx.

## Available Tools
scrape (firecrawl), search_web, RunPython, Write, docwriter skill.

If `scrape` is unavailable, ask the user to paste page source or key pages' HTML, and audit from that.

## Workflow

### Step 1: Scope the audit
Get the target URL. Default scope: homepage + up to 10 key pages (main nav links, top landing pages). Ask the user only if the site is huge or they want specific sections.

### Step 2: Crawl pages
`scrape` the homepage, extract internal links, then `scrape` the selected pages. Save raw HTML/markdown per page to the workspace for evidence.

### Step 3: Run the checklist per page
Use RunPython (requests/BeautifulSoup on saved HTML, or parse the scraped markdown) to check:
- **Title**: exists, 30-60 chars, unique per page
- **Meta description**: exists, 70-160 chars, unique
- **Headings**: exactly one H1; H2/H3 hierarchy not skipping levels
- **Content**: word count >= ~300 for indexable pages; image alt attributes
- **Technical**: canonical tag, robots meta, HTTPS, viewport tag (mobile), lang attribute
- **Performance signals**: page weight, number of render-blocking scripts (from HTML evidence; note if a real speed test needs external tooling)
- **Internal links**: orphan pages, broken links (HEAD-check a sample via RunPython), anchor text quality
- **Structured data**: presence of JSON-LD schema

### Step 4: Grade by severity
Classify every finding:
- **P0 Critical** — blocks indexing/ranking (noindex, missing title, broken canonical)
- **P1 High** — hurts ranking (duplicate titles, missing H1, thin content)
- **P2 Medium** — optimization opportunities (long meta, missing alt, weak anchors)
- **P3 Low** — nice-to-have

### Step 5: Export report
1. `.xlsx` issue tracker via RunPython: columns = page, check, severity, issue, evidence, recommended fix.
2. Report `.md`/`.docx` via docwriter skill: health summary, issue counts by severity, top-5 priority fixes, detailed list.
Tell the user the files are downloadable from the conversation.

## Quality Rules
- Every issue must cite the page URL and the evidence (element/value found).
- Never claim ranking impact guarantees — phrase fixes as best practices.
- If a page fails to scrape, record it as an issue itself (possible crawlability problem).
