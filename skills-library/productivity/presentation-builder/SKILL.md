---
name: presentation-builder
description: Presentation outline and content generation workflow — creates slide-by-slide outlines with speaker notes, visual suggestions, and narrative flow. Supports multiple presentation styles (pitch deck, training, conference, internal).
version: 1.0.0
category: productivity
when_to_use: User asks to create a presentation, slide deck, pitch, training material, or conference talk outline.
---

# Presentation Builder Skill — 演示文稿生成

## Goal
From a topic and audience context, produce a complete slide-by-slide outline with content, speaker notes, and visual suggestions. Export as a structured document or editable pptx.

## Available Tools
RunPython, Write, docwriter skill, search_web.

## Workflow

### Step 1: Audience & Context Analysis
Clarify with the user:
- Presentation type: pitch, training, conference, internal review
- Audience: executives, technical, mixed, general public
- Duration: 5 min lightning talk to 60 min keynote
- Key message: the one thing the audience should remember
- Format: slides, demo, interactive, recorded

### Step 2: Research (if needed)
If the topic requires factual support:
- Search for relevant statistics, case studies, quotes
- Verify data freshness (last 2 years preferred)
- Gather competitor or industry context

### Step 3: Narrative Arc
Build the story structure:
- **Hook** (1-2 slides): grab attention, state the problem
- **Context** (1-2 slides): why this matters now
- **Solution/Body** (60% of slides): main content, evidence, examples
- **Action** (1-2 slides): what the audience should do next
- **Close** (1 slide): memorable takeaway + contact

### Step 4: Slide-by-Slide Outline
For each slide, specify:
- **Title**: under 8 words, action-oriented
- **Content**: 3-5 bullet points, one idea per slide
- **Visual suggestion**: chart type, image concept, diagram
- **Speaker notes**: 2-3 sentences of what to say
- **Transition**: how to bridge to the next slide

### Step 5: Export
- Write outline as a structured markdown file
- If pptx requested, use RunPython with python-pptx
- Include speaker notes in the notes section of each slide

## Quality Rules
- One idea per slide — no wall of text
- Font sizes: title 30pt+, body 20pt+ for live presentations
- Maximum 5 bullet points per slide
- Use data visualization instead of text tables
- First and last slides must be the strongest