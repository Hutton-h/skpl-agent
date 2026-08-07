---
name: lead-enrichment
description: Lead list enrichment workflow. Takes a user-provided list of company names or domains, searches each one to fill in size, industry, contacts and social profiles, and writes back an updated lead file.
version: 1.0.0
category: sales
when_to_use: User has an existing lead/company list (xlsx/csv/text) that is missing fields and asks to enrich, complete, or update it with researched information.
---

# Lead Enrichment Skill — 线索补全

## Goal
Take the user's partial lead list and return the same list with researched fields filled in, every addition traceable to a source.

## Available Tools
Read, search_web, scrape (firecrawl), RunPython, Write.

If `search_web` is unavailable, tell the user enrichment requires web lookup and ask them to provide materials per company, or accept a format-cleanup-only pass.

## Workflow

### Step 1: Ingest the input list
- `Read` the user's file (xlsx/csv via RunPython+pandas; txt/md via Read).
- Identify the key column (company name or domain). Report row count and which target fields are missing.
- Default enrichment fields: industry, company size, headquarters, website, contact person, role, public email, phone, LinkedIn/社媒, latest news signal.

### Step 2: Per-company research loop
For each company (batch of 10, report progress):
1. If only a name: `search_web` "<name> official site" to resolve the domain.
2. `scrape` homepage + about/contact pages.
3. `search_web` "<name> employees / 融资 / 招聘" for size signals; "<name> LinkedIn" for the social URL.
4. Fill fields; store `source_url` per enriched row.
每行新增信息都必须带来源链接。

### Step 3: Normalize & flag
- Normalize formats (phone, URL, country/region naming).
- Confidence flag per row: `high` (official site), `medium` (directory/news), `low` (single weak source).
- Companies not found: keep the row, mark `status = not_found`, never invent data.

### Step 4: Write back the enriched file
RunPython -> update the original structure, save as `<original>-enriched.xlsx`:
- Original columns preserved; new/updated fields filled; plus `source_url`, `confidence`, `enriched_at` columns.
- Second sheet `summary`: total rows, enriched %, not-found list.
Tell the user the file is downloadable from the conversation.

### Step 5: Report
Short chat summary: how many enriched, how many not found, any notable discoveries (e.g. a lead just raised funding = hot).

## Quality & Compliance Rules
- Never overwrite user data silently — put enriched values in the same fields but keep originals in `<field>_original` when they differ.
- Public business info only; respect privacy laws.
- Mark uncertain data `low` confidence rather than presenting it as fact.
