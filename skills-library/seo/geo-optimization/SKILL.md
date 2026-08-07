---
name: geo-optimization
description: Generative Engine Optimization workflow. Optimizes content for AI search engines (ChatGPT, Perplexity, Doubao) using Q&A-style structure, authoritative citations, and structured data recommendations.
version: 1.0.0
category: seo
when_to_use: User wants content or a website optimized for AI search/answer engines (GEO/AEO), asks how to get cited by ChatGPT/Perplexity/豆包, or wants existing content restructured for AI visibility.
---

# GEO Skill — 生成式引擎优化（AI 搜索优化）

## Goal
Make the user's content more likely to be surfaced, quoted, and cited by AI answer engines (ChatGPT, Perplexity, Gemini, 豆包, Kimi), delivered as an optimization plan + rewritten content files.

## Available Tools
scrape (firecrawl), search_web, Write, RunPython, docwriter skill, translator skill (for multilingual versions).

If `scrape`/`search_web` are unavailable, ask the user to paste the content to optimize and proceed in pure-rewrite mode.

## Workflow

### Step 1: Baseline check
- If a URL is given: `scrape` the target pages.
- If text is given: work from the paste.
- Optional probe: `search_web` 2-3 questions the content should answer, note whether/how the brand currently appears in results.

### Step 2: Diagnose against GEO criteria
Score the content 1-5 on:
- **Answer-first structure** — direct answers in the first 1-2 sentences of each section
- **Q&A coverage** — headings phrased as real user questions
- **Citable facts** — statistics, definitions, named entities that AI can quote
- **Authority signals** — citations to reputable sources, author/org info, dates
- **Machine readability** — clean headings, lists, tables; schema markup present
- **Freshness** — visible publish/update dates

### Step 3: Restructure the content
Rewrite per section:
1. Question-style H2/H3 headings ("什么是…", "How much does … cost")
2. A 40-80 word direct answer immediately under each heading (snippet-ready 可直接引用)
3. Supporting detail with numbers, examples, and source citations
4. An FAQ block (5-8 Q&As) at the end
5. Summary table where comparisons exist

### Step 4: Structured data & technical recommendations
Provide ready-to-add JSON-LD snippets (FAQPage, Article, Organization, Product as appropriate) in a separate `.json`/`.md` file, plus checklist: author byline, last-updated date, canonical, llms.txt consideration.

### Step 5: Deliver files
- Optimized content `.md` (or `.docx` via docwriter skill)
- `schema-snippets.json` + implementation checklist `.md`
- Before/after diagnosis summary in the chat
Tell the user all files are downloadable from the conversation.

## Quality Rules
- Do not stuff keywords or invent fake statistics — AI engines penalize low-credibility content.
- Keep the brand's original tone; optimize structure, not voice.
- Note honestly: GEO improves odds of citation, it cannot guarantee it.
