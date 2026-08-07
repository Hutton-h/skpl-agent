---
name: skill-router
description: Meta-skill that helps the agent choose the most appropriate skill for a given task. Analyzes the user's request and routes to the best-matching skill from the library.
version: 1.0.0
category: automation
when_to_use: Automatically triggered when the agent needs to determine which skill to use for a complex or ambiguous request.
---

# Skill Router — 技能路由

## Goal
Analyze the user's request → match against available skills' `when_to_use` conditions → recommend the best skill(s) to invoke.

## Available Tools
Read (to scan SKILL.md files), Grep.

## Workflow

### Step 1: Intent Analysis
Parse the user's request for:
- Task type (research, coding, writing, analysis, automation)
- Explicit skill mentions
- Keywords matching skill descriptions

### Step 2: Skill Matching
For each available skill, compute a relevance score:
- Exact match on `when_to_use` condition → high
- Keyword overlap with `description` → medium
- Same category as the task type → low

### Step 3: Recommendation
Return the top 1-3 matching skills with:
- Skill name and description
- Match rationale
- Suggested invocation order (if multiple)

## Quality Rules
- Never recommend more than 3 skills at once
- If no skill matches well, suggest using the general agent
- Prefer specialized skills over general ones
