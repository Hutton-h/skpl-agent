---
name: deep-research
description: Multi-round deep research with source cross-validation. Runs iterative search rounds, requires at least two independent sources per key fact, attaches citation links, and outputs a structured research report file.
version: 1.0.0
category: research
when_to_use: User asks for in-depth/deep research on a complex topic, needs verified facts with citations, or wants a thorough investigation beyond a quick summary.
---

# Deep Research Skill — 深度调研（多轮搜索 + 交叉验证）

## Goal
Produce a citation-backed, cross-validated research report file for complex questions where accuracy matters more than speed.

## Available Tools
search_web, scrape (firecrawl), Write, RunPython, docwriter skill.

If `search_web` is unavailable, explain the limitation and ask the user to paste source materials; then run only the synthesis steps.

## Workflow

### Step 1: Decompose the question
Break the user's topic into 4-8 sub-questions. State them briefly so the user can correct scope before you burn search rounds.

### Step 2: Round-based searching (2-4 rounds)
- Round 1 (broad): one query per sub-question via `search_web`.
- Round 2 (deep): `scrape` the best 5-10 pages; extract claims, data, quotes.
- Round 3+ (gap-filling): search only for unanswered sub-questions or contradictions found earlier.
每个关键事实都要记录来源 URL 和访问日期。

### Step 3: Cross-validation gate (MANDATORY)
For every KEY fact (numbers, dates, causal claims):
- Require >= 2 independent sources agreeing, OR
- Mark it as "[single-source]" / "[disputed]" with the conflicting views shown.
Drop claims that fail and cannot be responsibly hedged.

### Step 4: Structured synthesis
Report structure:
1. Executive summary
2. Findings per sub-question (each with inline citation links)
3. Conflicts & uncertainties (what sources disagree on)
4. Conclusions & implications
5. Full source list: title — URL — access date
正文用中文还是英文跟随用户语言；引用链接保留原文。

### Step 5: Export via docwriter
- Default `.docx` (Write gen script + RunPython, python-docx) or `.md` via Write.
- Tell the user the file is downloadable from the conversation.

## Quality Rules
- No uncited key claims. Opinion/analysis sections must be labeled as such.
- Prefer primary sources (official docs, filings, papers) over aggregators.
- Budget awareness: if the topic is huge, deliver a solid v1 and offer a deeper round, rather than searching endlessly.
