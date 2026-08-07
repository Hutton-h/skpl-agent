---
name: market-research
description: End-to-end market research workflow. Defines the research question, runs multi-keyword web searches, synthesizes market size, trends and key players, and delivers a structured report file via the docwriter skill.
version: 1.0.0
category: research
when_to_use: User asks for market research, industry analysis, market size/trend investigation, or wants to understand a market before entering it.
---

# Market Research Skill — 市场调研

## Goal
Turn a vague market question into a sourced, structured market report file (md/docx) the user can download.

## Available Tools
search_web, scrape (firecrawl), RunPython, Write, docwriter skill.

If `search_web` is unavailable, STOP searching and ask the user to provide source materials (links, PDFs, notes), then continue from Step 4 with that material.

## Workflow

### Step 1: Frame the research question
Clarify in ONE round (ask only if genuinely ambiguous):
- Target market / industry / geography
- Time horizon (current state vs 3-5 year outlook)
- Deliverable format (default: docx via docwriter)

Rewrite the user request into 1-3 concrete research questions. 把模糊需求改写成可回答的调研问题。

### Step 2: Multi-keyword search plan
Build 4-8 search queries covering different angles:
- "<market> market size 2024 2025 forecast"
- "<market> industry trends / growth drivers"
- "<market> major players / leading companies / market share"
- "<market> 中国市场 / 行业报告" (add Chinese queries if relevant)
Run `search_web` in parallel batches. Keep every source URL.

### Step 3: Deep-read top sources
Use `scrape` on the 3-6 most authoritative results (research firms, official statistics, company filings, reputable media). Extract numbers, dates, and claims. Discard SEO spam and content farms.

### Step 4: Synthesize findings
Organize into the report skeleton:
1. Executive summary (3-5 bullet takeaways)
2. Market size & growth (with figures + source links)
3. Key trends & drivers
4. Competitive landscape / major players
5. Opportunities & risks
6. Conclusion & suggested next steps
Cross-check any critical number against at least 2 sources; flag conflicts explicitly.

### Step 5: Generate the report file
Use the **docwriter** skill:
- .md or .html via Write directly; .docx via Write a Python script + RunPython (python-docx).
- Include a source list with URLs at the end.
- Tell the user the file is downloadable from the conversation.

## Quality Rules
- Never invent market figures — every number must trace to a scraped source or be marked as an estimate.
- Prefer sources < 2 years old; state the data date next to each figure.
- Keep the report under ~2000 words unless the user asks for depth.
