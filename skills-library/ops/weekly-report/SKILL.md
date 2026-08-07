---
name: weekly-report
description: Periodic report generation workflow. Collects the user's weekly data and work items, structures them into completed/in-progress/risks/next-week-plan sections, and generates a docx or md report via the docwriter skill.
version: 1.0.0
category: ops
when_to_use: User asks to write a weekly/monthly/quarterly work report, 周报/月报, progress summary, or team status report from their provided notes and data.
---

# Weekly Report Skill — 周期报告（周报/月报）

## Goal
Turn the user's scattered weekly notes/metrics into a clean, structured report file (docx/md) ready to send to managers or the team.

## Available Tools
Read, RunPython (pandas for metrics files), Write, docwriter skill.

## Workflow

### Step 1: Collect inputs
Ask the user for (accept messy input — bullets, fragments, chat logs):
- This week's work items & outcomes
- Key metrics/data (paste or file: xlsx/csv -> RunPython profile)
- Blockers/risks
- Next week's intentions
If the user already dumped everything, skip asking and proceed. 用户给了材料就直接做，不反复追问。

### Step 2: Structure into the report skeleton
Default sections (adapt to their org's template if provided):
1. **本周完成 Completed** — item + outcome + metric evidence (quantify: "完成 X，环比 +Y%")
2. **进行中 In Progress** — item + current % + expected completion
3. **风险与阻塞 Risks/Blockers** — issue + impact + needed support
4. **下周计划 Next Week Plan** — item + owner + target date
5. **数据亮点 Data Highlights** (optional) — 2-4 key metrics with deltas
Rules: every item one line, verb-first, numbers over adjectives. 每条一行，动词开头，用数字说话。

### Step 3: Polish language
- Merge duplicates, split compound items, remove filler.
- Tone: factual, confident, no self-deprecation, no exaggeration.
- Team version vs manager version: ask only if relevant; default = manager version.

### Step 4: Generate the file
Via docwriter skill:
- `.docx` (default for formal submission): Write a gen script + RunPython (python-docx) — title "工作周报 <name/team> <date range>", generation date, section headings, tables for metrics.
- `.md` via Write if the user prefers plain text.
Tell the user the file is downloadable from the conversation.

### Step 5: Summary in chat
Paste the report body inline too (it is short), so the user can eyeball before downloading.

## Quality Rules
- Never invent accomplishments or metrics — only restructure what the user provided; use [待补充] placeholders for gaps.
- Keep the whole report <= 1 page unless the user asks for detail.
- Date range in the title must match the actual week (confirm timezone/locale: 周一至周日 vs 周日至周六).
