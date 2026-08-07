---
name: sales-playbook
description: Sales playbook creation workflow. Distills product selling points, maps common objections to responses, writes opening-line templates, and customizes everything per industry into a playbook file.
version: 1.0.0
category: sales
when_to_use: User asks for sales scripts/talk tracks, objection-handling guidance, opening lines for calls or meetings, or an industry-customized sales playbook.
---

# Sales Playbook Skill — 销售话术手册

## Goal
Produce a practical, industry-customized sales playbook file the team can use on calls, in meetings, and in messages.

## Available Tools
search_web, scrape (firecrawl), Write, RunPython, docwriter skill, translator skill.

If `search_web` is unavailable, build the playbook from the user's provided product/industry material only.

## Workflow

### Step 1: Collect product inputs
Ask once for whatever is missing: product description, 3-5 differentiators, pricing model, target industries, 2-3 customer proof points (results/numbers). If the product has a website, `scrape` it instead of asking.

### Step 2: Distill selling points
Convert features into benefit statements:
`feature -> customer benefit -> proof -> one-line talk track`
Produce 3-5 core value propositions, each with a 10-second and a 60-second spoken version. 卖点要口语化，能直接说出口。

### Step 3: Objection-response matrix
List 8-12 likely objections for this product/industry, e.g.:
"太贵了 / too expensive", "我们已经有供应商了 / happy with current vendor", "没时间 / no time", "先发个资料吧 / just send info", "需要考虑 / need to think".
For each: acknowledge line -> reframe -> evidence -> next-step question. Keep every response <= 3 sentences, spoken-style.

### Step 4: Opening templates
Provide openers per channel:
- Cold call first 10 seconds (2 variants)
- Walk-in / meeting opening (2 variants)
- WeChat/WhatsApp first message (2 variants)
- Voicemail / follow-up opener (1 variant)
Each with a brief "why this works" note.

### Step 5: Industry customization
For each target industry (up to 3): vocabulary the industry uses, top 2 pains, which value prop leads, one industry-specific objection+response. Optionally `search_web` the industry's current hot topics to sound current.

### Step 6: Export playbook
Via docwriter skill -> `.docx` (default, team-printable) or `.md`:
sections = value props, talk tracks, objection matrix, openers, industry pages, do/don't list.
Tell the user the file is downloadable from the conversation.

## Quality Rules
- Everything must be speakable — read each line mentally; cut anything that sounds written.
- Never invent customer names or results; use placeholders like [客户案例A] when proof is missing.
- Compliant selling only: no denigrating competitors, no unverifiable superlatives.
