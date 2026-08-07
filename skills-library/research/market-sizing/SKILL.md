---
name: market-sizing
description: Market sizing workflow — estimates TAM, SAM, SOM with bottom-up and top-down approaches, validates with industry data.
version: 1.0.0
category: research
when_to_use: User asks to estimate market size, calculate TAM/SAM/SOM, or assess market opportunity.
---
# Market Sizing Skill — 市场规模估算

## Goal
From a market or product category → estimate TAM, SAM, SOM → validate with multiple approaches → produce a market sizing report.

## Available Tools
search_web, scrape, RunPython, docwriter skill, publish_visual.

## Workflow

### Step 1: Market Definition
- Define the market scope and boundaries
- Identify the customer segments
- Determine the geographic scope

### Step 2: Top-Down Estimation
- Start with industry-wide data (reports, government statistics)
- Narrow down by segment, geography, and product fit
- Apply growth rates and adjustments

### Step 3: Bottom-Up Estimation
- Estimate unit economics (price, volume)
- Multiply by addressable customer count
- Cross-reference with top-down results

### Step 4: TAM / SAM / SOM
- TAM: Total Addressable Market (theoretical maximum)
- SAM: Serviceable Addressable Market (your reachable segment)
- SOM: Serviceable Obtainable Market (realistic capture)

### Step 5: Report
Produce a market sizing report with:
- Methodology explanation
- TAM/SAM/SOM estimates with sources
- Visual charts (pie/donut for market share)
- Confidence intervals and assumptions

## Quality Rules
- Always cite the source and date of industry data
- Use both top-down and bottom-up for cross-validation
- Clearly state all assumptions and their impact
- Mark estimates with confidence levels
