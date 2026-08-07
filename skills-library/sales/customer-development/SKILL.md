---
name: customer-development
description: B2B customer development workflow. Defines the ideal customer profile, finds target companies via web search, extracts contact info, and exports a lead list xlsx with company, website, contact, email and source.
version: 1.0.0
category: sales
when_to_use: User asks to find potential customers, build a prospect/lead list, do outbound customer development, or identify target companies matching an ICP.
---

# Customer Development Skill — 客户开发

## Goal
From an Ideal Customer Profile (ICP) to a downloadable lead list xlsx with verifiable sources.

## Available Tools
search_web, scrape (firecrawl), RunPython, Write, Read.

If `search_web` is unavailable, ask the user to provide company names/domains or an existing list, and run only the extraction/structuring steps.

## Workflow

### Step 1: Define the ICP
Confirm with the user (one round max):
- Industry / vertical, company size (employees/revenue), geography
- Buyer role (who signs: CEO/Procurement/Ops...)
- Pain point the product solves
Write the ICP as 3-5 concrete filters. 把画像写成可筛选条件。

### Step 2: Source target companies
`search_web` with ICP-driven queries:
- "<industry> companies in <region>", "top <niche> startups", "<industry> 企业名录/排行榜"
- Directories, associations, exhibition exhibitor lists, job boards (companies hiring relevant roles)
`scrape` the promising list pages. Collect 20-50 candidate companies (or the user's target count).

### Step 3: Extract contact info per company
For each candidate:
- `scrape` the official site: contact page, about page, footer
- Capture: company name, website, location, size signal, contact person (if public), public email/phone, LinkedIn/social URL
- Record the exact source URL for every email found. 只收集公开渠道信息。
- Skip companies clearly outside the ICP; note why.

### Step 4: Validate & dedupe
RunPython: dedupe by domain, flag rows missing email, basic email format check (regex), drop obvious generic inboxes into a separate column note (info@/sales@ are lower value).

### Step 5: Export lead list xlsx
RunPython (openpyxl/pandas) -> `leads-<date>.xlsx`, columns:
`company | website | industry | size_signal | location | contact_name | role | email | linkedin | source_url | icp_fit(1-5) | notes`
Bold header, frozen row, autofilter. Tell the user the file is downloadable from the conversation.

## Quality & Compliance Rules
- Only collect publicly published business contact info; never guess/fabricate emails.
- No personal/private data. Business contacts only, with source URLs for traceability.
- Remind the user to comply with anti-spam laws (CAN-SPAM/GDPR/《个人信息保护法》) when using the list.
