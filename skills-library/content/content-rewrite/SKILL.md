---
name: content-rewrite
description: Multi-platform content repurposing workflow. Rewrites one core piece of content into platform-native versions for WeChat Official Account, Zhihu, Xiaohongshu, LinkedIn and X/Twitter, respecting each platform's style.
version: 1.0.0
category: content
when_to_use: User has one article/post and wants it rewritten or adapted for multiple platforms (公众号/知乎/小红书/LinkedIn/Twitter), or asks for cross-platform content distribution.
---

# Content Rewrite Skill — 内容改写分发

## Goal
Turn ONE core content piece into N platform-native versions, each feeling originally written for that platform — not copy-pasted.

## Available Tools
Read, scrape (firecrawl), Write, translator skill (for language conversion), docwriter skill.

## Workflow

### Step 1: Ingest the core content
- User pastes text, gives a file (`Read`), or gives a URL (`scrape`).
- Extract: core message (1 sentence), 3-5 key points, target audience, CTA.

### Step 2: Confirm target platforms
Default set (adjust to user): 公众号, 知乎, 小红书, LinkedIn, X/Twitter. Ask which subset if not specified — or proceed with all five.

### Step 3: Rewrite per platform rules
Apply each platform's native style:

**公众号 (WeChat OA)**: strong title (悬念/数字/冲突), short paragraphs (<= 3 lines), 800-1500 words, subheadings, ending with 互动提问 + 关注引导.

**知乎 (Zhihu)**: answer-style opening ("先说结论"), logic-driven structure, data/ citations welcome, 1000-2000 words, professional tone, first-person experience framing.

**小红书 (Xiaohongshu)**: emoji-friendly but not overloaded, title <= 20 chars with keywords, 清单体/攻略体, 300-600 words, 5-10 hashtags, personal & authentic voice ("姐妹们/亲测").

**LinkedIn**: professional insight angle, hook first line, 150-300 words, short lines, 3-5 hashtags, end with a discussion question.

**X/Twitter**: thread of 4-8 tweets, each <= 280 chars, first tweet = hook that works standalone, one idea per tweet, final tweet = CTA.

### Step 4: Language handling
If platforms need a different language than the source (e.g. Chinese source -> LinkedIn English), delegate via the **translator** skill instead of inline translation.

### Step 5: Export
Write one `.md` file per platform: `<topic>-<platform>.md`, each containing final copy + title options (2-3) + hashtags/tags where relevant. Optionally bundle all into one `.docx` via docwriter skill.
Tell the user the files are downloadable from the conversation.

## Quality Rules
- Preserve facts and key points; change packaging, not meaning.
- Each version must pass the "native test": would a regular user of that platform notice it's a cross-post? If yes, rewrite.
- Respect platform limits (title lengths, character caps, hashtag counts).
- Never fabricate engagement bait claims ("必看" "震惊") the content can't back up.
