---
name: sales-intelligence
description: Sales intelligence workflow — company research, SWOT analysis, objection handling, and battle card generation. Builds a structured sales brief with competitive positioning and actionable talking points.
version: 1.0.0
category: sales
when_to_use: User asks to prepare for a sales call, research a prospect company, build a battle card, or needs SWOT and objection-handling materials for a specific competitor or prospect.
---

# Sales Intelligence Skill — 销售情报

## Goal
From a target company name and competitor context, produce a structured sales brief: company overview → SWOT → objection handling → battle card → downloadable file.

## Available Tools
search_web, scrape (firecrawl), RunPython, Write, docwriter skill, publish_visual.

## Workflow

### Step 1: Company Research
Use search_web to gather:
- Company size, industry, revenue range
- Key decision-makers (LinkedIn/public profiles)
- Recent news / funding / product launches
- Technology stack (if publicly available)

### Step 2: SWOT Analysis
Synthesize findings into Strengths / Weaknesses / Opportunities / Threats:
- Strengths: what they do well, market position
- Weaknesses: gaps, negative reviews, churn signals
- Opportunities: where your solution fits
- Threats: competitor moves, market shifts

### Step 3: Objection Handling
For each likely objection, write a 2-3 sentence response:
- "We already use X" → differentiation
- "Too expensive" → ROI framing
- "Not a priority" → urgency building
- "Need to think about it" → next-step anchoring

### Step 4: Battle Card
Condense into a one-page battle card with:
- Competitor snapshot (3 bullets)
- Your key differentiators (3 bullets)
- Pricing comparison (if available)
- 3 killer questions to ask the prospect

### Step 5: Deliver
Use publish_visual to show the SWOT/Comparison table, then docwriter to export the full brief as a file.

## Quality Rules
- Every claim must cite a source (URL or search snippet)
- SWOT must be balanced — acknowledge real competitor strengths
- Never fabricate pricing or revenue numbers; mark estimates with "~"
- Keep battle card under one page