---
name: trend-analysis
description: Trend identification and signal detection workflow — scans news, social media, patents, and research papers to identify emerging trends, assess technology maturity, and produce a trend radar report.
version: 1.0.0
category: research
when_to_use: User asks to identify trends, detect weak signals, assess technology maturity, build a trend radar, or understand what's emerging in an industry or technology space.
---

# Trend Analysis Skill — 趋势分析

## Goal
From a domain or technology area, scan multiple sources → identify emerging trends and weak signals → assess maturity → produce a trend radar visualization and report.

## Available Tools
search_web, scrape (firecrawl), RunPython, publish_visual, docwriter skill.

## Workflow

### Step 1: Source Scanning
Use search_web to gather signals from multiple source types:
- **News**: recent announcements, product launches, partnerships
- **Funding**: VC investments, acquisitions, IPO filings
- **Patents**: new filings in the domain
- **Research**: recent papers, conference talks, open-source activity
- **Social**: Hacker News, Reddit, Twitter/X discussions

### Step 2: Signal Extraction
For each source, extract:
- **Signal**: what is the emerging trend or change?
- **Strength**: how many independent sources mention it?
- **Velocity**: is it accelerating or fading?
- **Impact**: potential effect on the industry (high/medium/low)

### Step 3: Trend Classification
Map each trend to a maturity framework:
- **Emerging**: early signals, few sources, high uncertainty
- **Growing**: increasing mentions, early adoption, funding
- **Peaking**: mainstream coverage, enterprise adoption
- **Declining**: saturation, replacement technologies emerging

### Step 4: Trend Radar Visualization
Use publish_visual to create a radar chart:
- **Rings**: Emerging → Growing → Peaking → Declining
- **Dots**: each trend positioned by maturity and impact
- **Size**: proportional to signal strength
- **Color**: industry sector or technology category

### Step 5: Report Generation
Produce a structured trend report:
- Executive summary: top 3 trends to watch
- Trend profiles: one page per trend with evidence and assessment
- Recommendations: strategic implications and action items
- Methodology: sources consulted, date range, confidence levels

## Quality Rules
- Always cite the date range of the scan
- Distinguish between "trend" (sustained) and "fad" (short-lived)
- Cross-validate signals across at least 2 independent sources
- Mark confidence levels: high/medium/low for each trend
- Never present a single source as a trend