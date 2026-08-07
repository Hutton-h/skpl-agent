---
name: fact-checker
description: Fact verification workflow — takes a claim or statement, traces it to original sources, cross-references multiple independent sources, and produces a credibility assessment with source citations.
version: 1.0.0
category: research
when_to_use: User asks to verify a claim, fact-check a statement, trace information to its source, or assess the credibility of an article or report.
---

# Fact Checker Skill — 事实核查

## Goal
From a claim or statement, trace to original sources → cross-reference multiple independent sources → assess credibility → produce a structured verification report with citations.

## Available Tools
search_web, scrape (firecrawl), RunPython.

## Workflow

### Step 1: Claim Extraction
Parse the user's input to identify individual claims:
- Break compound statements into atomic claims
- Each claim should be independently verifiable
- Identify the type: factual (numeric), attribution (who said what), causal (X caused Y)

### Step 2: Source Tracing
For each claim:
1. Search for the claim text to find original sources
2. Trace to the earliest known publication
3. Identify the original source (person, organization, study)
4. Check if the claim has been misattributed or taken out of context

### Step 3: Cross-Reference
Verify against multiple independent sources:
- **Primary sources**: original research, official statements, raw data
- **Secondary sources**: reputable news outlets, academic papers
- **Tertiary sources**: Wikipedia, encyclopedias (use as starting points only)
- **Contradictory sources**: actively search for opposing evidence

### Step 4: Credibility Assessment
Rate each claim on a 5-level scale:
- ✅ **Verified**: confirmed by multiple independent primary sources
- 🟢 **Likely True**: strong evidence, minor inconsistencies
- 🟡 **Unverified**: insufficient evidence to confirm or deny
- 🟠 **Misleading**: technically true but missing critical context
- 🔴 **False**: contradicted by primary sources

### Step 5: Verification Report
Produce a structured report:
- Claim-by-claim analysis with rating and rationale
- Source list with URLs and credibility notes
- Context: what the claim omits or distorts
- Overall assessment: is the source/article generally reliable?

## Quality Rules
- Every claim rating must cite at least one source
- Actively search for opposing evidence — don't just confirm
- Distinguish between "no evidence found" and "evidence contradicts"
- Flag when a source is the only one making a claim
- Date-stamp all sources — outdated information may no longer be accurate