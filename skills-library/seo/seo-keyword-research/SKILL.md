---
name: seo-keyword-research
description: Keyword research workflow. Expands seed keywords, classifies search intent, assesses difficulty and opportunity, and exports a keyword matrix as an xlsx file via RunPython.
version: 1.0.0
category: seo
when_to_use: User asks for keyword research, wants keyword ideas for SEO/content, or needs a keyword matrix with intent and priority for a topic or site.
---

# SEO Keyword Research Skill — 关键词研究

## Goal
Turn seed keywords into a prioritized keyword matrix (xlsx) with intent classification and opportunity scoring.

## Available Tools
search_web, scrape (firecrawl), RunPython, Write.

If `search_web` is unavailable, ask the user for their seed list and any competitor keywords they know, then do expansion/analysis from those.

## Workflow

### Step 1: Collect seeds
Get from the user: product/topic, target market & language, 3-10 seed keywords (propose seeds yourself if they have none), and main competitors (optional).

### Step 2: Expand the keyword pool
For each seed, generate expansions and verify via `search_web` (autocomplete-style queries, "people also ask", related searches visible in results, competitor pages via `scrape`):
- Modifiers: best / how to / vs / price / review / near me / 2026
- Long-tail question forms (what/why/how/which)
- Chinese + English variants if the market is bilingual
Target pool: 50-150 candidate keywords.

### Step 3: Classify search intent
Label every keyword with ONE intent:
- **Informational** 信息型 (how/what/guide)
- **Navigational** 导航型 (brand/login/official)
- **Commercial** 商业调研型 (best/vs/review/top)
- **Transactional** 交易型 (buy/price/discount/download)
Rule-based pass via RunPython + manual review for ambiguous terms.

### Step 4: Difficulty & opportunity scoring
Without paid tools, estimate with observable signals via `search_web` result inspection:
- Difficulty (1-5): authority of ranking domains, presence of big brands/forums, ad density
- Opportunity (1-5): intent-value x weakness of current results (forums/Ugc ranking = weak = opportunity)
- Priority = Opportunity - 0.5 x Difficulty (document the formula in the sheet)

### Step 5: Export keyword matrix xlsx
RunPython (openpyxl/pandas) -> `keyword-matrix.xlsx`, sheets:
1. **Matrix**: keyword, intent, difficulty, opportunity, priority, target page type, notes
2. **Clusters**: keywords grouped into 5-10 topic clusters with a suggested pillar page each
Bold headers, freeze top row, column widths, autofilter. Tell the user the file is downloadable.

## Quality Rules
- Never fabricate search-volume numbers; if no tool data, use difficulty/opportunity estimates only and say so.
- Deduplicate near-identical keywords; keep the most natural phrasing.
- Flag brand keywords of competitors separately (bidding/legal caution).
