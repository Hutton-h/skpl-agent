---
name: requirement-clarify
description: Requirement clarification workflow — audits the current state before taking action, separates model inference from user statements, and ensures alignment before execution. Never assumes, always asks.
version: 1.0.0
category: coding
when_to_use: User gives an ambiguous request, a complex task with unclear constraints, or when the agent should pause and verify understanding before proceeding.
---

# Requirement Clarification Skill — 需求澄清

## Goal
Before executing a task: audit current state → identify ambiguities → separate known facts from inferred assumptions → ask clarifying questions → get explicit confirmation → then proceed.

## Available Tools
Read, Glob, Grep, RunPython.

## Core Principle — 核心原则
**模型推断与用户原话严格隔离。** Never present an inference as a fact. Always label: "You said X" vs "I'm inferring Y from X — is that correct?"

## Workflow

### Step 1: State Audit
Gather relevant context without making changes:
- Read relevant files, configs, and documentation
- Identify the current state of the codebase or system
- Note any constraints visible in the environment

### Step 2: Requirement Decomposition
Break the user's request into atomic parts:
- **Facts**: what the user explicitly stated
- **Inferences**: what can be reasonably assumed (mark as such)
- **Gaps**: what is missing and must be asked

### Step 3: Ambiguity Detection
Flag potential misunderstandings:
- Vague terms ("optimize", "fix", "improve")
- Missing constraints (time, budget, scope)
- Conflicting requirements (speed vs quality)
- Undefined success criteria

### Step 4: Clarification Questions
Present 2-5 focused questions, ordered by impact:
- Most critical/blocking question first
- Each question should have a clear default assumption
- Avoid yes/no questions when possible — ask for specifics

Example:
```
I understand you want to [task]. Before I start, I need to clarify:

1. [Critical question] — my assumption is [X], but this could also be [Y]
2. [Scope question] — should I include [A] or limit to [B]?
3. [Constraint question] — what's your priority: speed or thoroughness?

My current understanding: [summary]. Is this correct?
```

### Step 5: Confirmation Gate
Do NOT proceed until the user confirms. If the user says "just do it", present the assumptions you're proceeding with and ask for a one-word confirmation.

## Quality Rules
- Never proceed with a task that has unresolved critical ambiguities
- Always distinguish "you explicitly said" from "I'm inferring"
- When the user says "whatever you think is best", still present your reasoning
- If the user pushes back on a question, drop it — don't argue