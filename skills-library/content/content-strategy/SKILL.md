---
name: content-strategy
description: Content strategy workflow. Defines the target audience, builds 3-5 content pillars, generates a 30-day content calendar as xlsx, and recommends channel distribution tactics.
version: 1.0.0
category: content
when_to_use: User asks for a content strategy, content plan/calendar, topic planning for social media or blog, or channel distribution recommendations.
---

# Content Strategy Skill — 内容策略

## Goal
Deliver a content strategy package: audience definition, content pillars, a 30-day content calendar (xlsx), and channel distribution advice.

## Available Tools
search_web, scrape (firecrawl), RunPython, Write, docwriter skill.

If `search_web` is unavailable, skip trend research and build from the user's business inputs only.

## Workflow

### Step 1: Gather inputs (one round)
Brand/product, goal (awareness/leads/conversion), available channels (公众号/知乎/小红书/抖音/LinkedIn/X/blog), posting capacity (posts/week), any existing content that performed.

### Step 2: Audience snapshot
Define 1-2 core audience segments: who they are, their top 3 questions/pains, where they consume content. Optionally `search_web` "<industry> 用户痛点 / trending topics" to ground this.

### Step 3: Content pillars (3-5)
Create pillars at the intersection of `audience pains x brand expertise x business goal`. For each pillar: name, purpose, example topics (5+), best-fit formats (图文/短视频/长文), primary channel.
示例支柱：行业科普、产品教程、客户案例、观点评论、幕后故事。

### Step 4: 30-day content calendar
RunPython -> `content-calendar-<month>.xlsx`, one row per planned post:
`date | weekday | pillar | topic/working title | format | channel | hook/angle | cta | status`
Rules when filling:
- Match cadence to the user's stated capacity (never over-schedule).
- Balance pillars (no pillar > 40% of slots).
- Mark seasonal/holiday hooks where relevant (check dates for the target month).
Bold header, frozen row, autofilter, pillar-colored rows optional.

### Step 5: Channel distribution advice
For each channel: posting frequency, best time windows (general heuristics), format adaptation notes, and 2-3 growth tactics. One core piece -> multi-platform repurposing chain (参见 content-rewrite skill).

### Step 6: Deliver
- `content-calendar.xlsx` (Step 4)
- Strategy summary `.md` via Write: audience, pillars, cadence, channels, KPIs to track (reads/follows/leads per channel).
Tell the user both files are downloadable from the conversation.

## Quality Rules
- Topics must be specific working titles, not vague themes ("如何" "5个方法" style, ready to write).
- Respect capacity: an empty calendar slot beats an unrealistic plan.
- No plagiarism: trend research informs topics, never copies content.
