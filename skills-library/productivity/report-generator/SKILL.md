---
name: report-generator
description: Structured report generation workflow — produces weekly reports, monthly reports, project reports, and analysis reports. Supports multiple formats (docx, xlsx, pdf, md, html) with consistent styling and data visualization.
version: 1.0.0
category: productivity
when_to_use: User asks to generate a report — weekly summary, monthly review, project status, analysis findings, or any structured document with data and narrative.
---

# Report Generator Skill — 报告生成

## Goal
From user-provided data and context, produce a structured, professionally formatted report with consistent styling and embedded data visualizations.

## Available Tools
RunPython, Write, docwriter skill, publish_visual.

## Workflow

### Step 1: Report Type Detection
Identify the report type from user's request:
- **Weekly/Monthly**: date range, KPIs, highlights, blockers
- **Project**: milestones, progress, risks, resource usage
- **Analysis**: data sources, methodology, findings, recommendations
- **Executive**: 1-page summary, key metrics, strategic implications

### Step 2: Data Collection
Gather all necessary data:
- From user-provided files or text
- From search results (if research report)
- From calculations (RunPython for aggregations)
- Validate completeness — flag missing data points

### Step 3: Structure Building
Assemble the report skeleton:
- **Cover page**: title, date, author, confidentiality
- **Executive summary**: 3-5 bullet points
- **Body sections**: one per key topic
- **Data visualizations**: charts inline with narrative
- **Conclusions & recommendations**: action-oriented
- **Appendix**: raw data, methodology notes

### Step 4: Visualization
Use publish_visual for inline charts:
- Trend lines for time-series data
- Bar charts for comparisons
- Pie/donut for composition
- Tables for detailed breakdowns

### Step 5: Format Selection & Export
Based on user's needs:
- **docx**: formal business reports, editable
- **xlsx**: data-heavy reports with pivot tables
- **pdf**: final distribution, non-editable
- **md/html**: internal wiki, quick sharing

Use RunPython with openpyxl/python-docx/fpdf for generation.

### Step 6: Delivery
Save to workspace and report the file path. Present a summary of key findings in the chat.

## Quality Rules
- Executive summary must be readable in under 60 seconds
- Every chart must have a title, axis labels, and source note
- Numbers over 1,000 must use thousands separators
- Date formats must be consistent throughout
- All data sources must be cited