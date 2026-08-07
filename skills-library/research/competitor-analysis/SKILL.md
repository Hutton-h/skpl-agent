---
name: competitor-analysis
description: Structured competitor analysis workflow. Builds the competitor list, researches each competitor's website, pricing, features and reviews, produces a comparison table plus SWOT, and exports a report file.
version: 1.0.0
category: research
when_to_use: User asks to analyze competitors, compare rival products, benchmark features/pricing, or wants a SWOT against competing offerings.
---

# Competitor Analysis Skill — 竞品分析

## Goal
Deliver a sourced competitor comparison (table + SWOT) as a downloadable file (xlsx/md/docx).

## Available Tools
search_web, scrape (firecrawl), RunPython, Write, docwriter skill.

If `search_web` is unavailable, ask the user to provide competitor URLs/materials and continue from Step 3 with those.

## Workflow

### Step 1: Lock the competitor list
- If the user named competitors, use them.
- Otherwise `search_web`: "<product/category> top competitors / alternatives", pick 3-7 real competitors. Confirm the list with the user in one short message (or proceed if they said "you decide").

### Step 2: Per-competitor research loop
For EACH competitor, gather via `search_web` + `scrape` of the official site:
- Positioning & target customer (homepage, about page)
- Pricing (pricing page — scrape it; record exact tiers/currency/date)
- Core features (features/product pages)
- Strengths & complaints (review sites, forums, social posts)
记录每家竞品的信息来源 URL，便于引用。

### Step 3: Build the comparison matrix
Dimensions (rows) x competitors (columns):
positioning, target segment, pricing model, entry price, key features (3-5), integrations, notable strengths, notable weaknesses, data source URL.
Generate `.xlsx` via RunPython (openpyxl): bold header, frozen first row, autofit-ish column widths.

### Step 4: SWOT analysis
For the user's product (or the market leader if unspecified), write a SWOT grounded ONLY in Step 2 evidence — no generic filler. Each quadrant 3-5 items, each item one sentence.

### Step 5: Report + export
Deliver two artifacts:
1. Comparison matrix `.xlsx` (Step 3).
2. Analysis report `.md` or `.docx` (via docwriter skill): summary, key differentiators, pricing insights, SWOT, strategic recommendations (3-5 actionable).
Tell the user both files are downloadable from the conversation.

## Quality Rules
- Pricing changes fast — always note the capture date next to pricing data.
- Mark unknown cells as "N/A (not found)" instead of guessing.
- Keep feature claims verifiable: link or cite the page each came from.
