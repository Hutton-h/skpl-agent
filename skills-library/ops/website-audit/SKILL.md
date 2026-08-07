---
name: website-audit
description: Website operations audit workflow. Scrapes the site, checks content update frequency, dead links, basic SEO and conversion paths, computes an operations health score, and exports an optimization checklist.
version: 1.0.0
category: ops
when_to_use: User asks to audit/review their website's operations health, check for dead links or stale content, evaluate conversion paths, or get a website optimization checklist.
---

# Website Audit Skill — 网站运营审计

## Goal
Give the site owner an operations health score plus a prioritized, actionable optimization checklist file.

## Available Tools
scrape (firecrawl), search_web, RunPython (link checking via requests), Write, docwriter skill.

If `scrape` is unavailable, ask the user for sitemap URLs or exported page lists and audit from those.

## Workflow

### Step 1: Scope
Get the site URL. Default: crawl homepage -> collect internal links (nav, footer, sitemap.xml if reachable) -> audit up to 30 representative pages (home, top nav, blog list + latest 5 posts, product/pricing, contact).

### Step 2: Content freshness check
- Blog/news: extract publish dates of latest posts -> compute days since last update, posting frequency over 90 days.
- Product/pricing pages: look for stale signals (old copyright years, "2023" promos, expired events).
记录每个板块的最后更新时间。

### Step 3: Dead link check
RunPython (requests HEAD/GET with timeout, concurrency ~10):
- Collect all hrefs from crawled pages; dedupe; check status codes.
- Report: 404s, 5xx, timeouts, redirect chains (>2 hops), broken image srcs.
Output table: `page_url | link_url | status | anchor_text`.

### Step 4: Basic SEO pass
Reuse seo-audit checks in light mode: title/meta presence & uniqueness, single H1, alt attributes, viewport (mobile), HTTPS, canonical, sitemap/robots presence. (Full deep SEO -> hand off to seo-audit skill.)

### Step 5: Conversion path check
Trace key journeys manually from crawled content:
- Homepage -> product -> pricing -> contact/purchase: count clicks, note friction (missing CTA, broken form link, no contact info above the fold).
- CTA inventory: list every CTA text+target; flag weak ones ("click here", dead-end pages).
- Contact options: form/phone/email/IM present and working (links resolve).

### Step 6: Health score + export
Score 0-100 across 5 dimensions (weights): freshness 20, link health 20, basic SEO 25, conversion path 25, technical basics 10. Show per-dimension subscores.
Deliver via docwriter skill:
1. `website-audit-<date>.md/.docx`: score card, findings by dimension, evidence URLs.
2. `optimization-checklist.xlsx` via RunPython: `priority | dimension | issue | page | recommendation | effort(S/M/L)`, sorted by priority.
Tell the user the files are downloadable from the conversation.

## Quality Rules
- Every finding cites its page URL; dead-link rows must be reproducible.
- Score is heuristic — explain the rubric in the report, don't present it as absolute truth.
- Distinguish "verified broken" from "could not verify" (timeout) items.
