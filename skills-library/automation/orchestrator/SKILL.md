---
name: orchestrator
description: Multi-model orchestration workflow — routes tasks through a three-layer architecture (Advisor → Orchestrator → Worker). The Advisor analyzes the task, the Orchestrator dispatches to specialized Workers, and results are aggregated.
version: 1.0.0
category: automation
when_to_use: User has a complex task that benefits from being decomposed into sub-tasks handled by specialized sub-agents or different models — research, analysis, writing, coding, and verification in parallel.
---

# Multi-Model Orchestrator Skill — 多模型编排

## Goal
Decompose a complex task into parallel sub-tasks, dispatch each to the most suitable agent/model, and aggregate results into a cohesive output.

## Available Tools
TeamCreate, AgentCreate, TaskCreate, TeamSay (sub-agent coordination). RunPython for data aggregation.

## Architecture — 三层架构
```
User Request
    │
    ▼
┌─────────────┐
│  Advisor     │ ← Analyzes the task, decomposes into sub-tasks, assigns workers
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Orchestrator │ ← Dispatches sub-tasks, monitors progress, handles failures
└──────┬──────┘
       │
       ├──────► Worker A (Research) ──► result
       ├──────► Worker B (Analysis) ──► result
       ├──────► Worker C (Writing)  ──► result
       └──────► Worker D (Review)   ──► result
                   │
                   ▼
            ┌─────────────┐
            │ Aggregator   │ ← Combines results, resolves conflicts, formats output
            └─────────────┘
```

## Workflow

### Step 1: Task Decomposition (Advisor)
Analyze the user's request and break it into atomic sub-tasks:
- Each sub-task should be independently executable
- Identify dependencies between sub-tasks
- Classify each sub-task by type: research, analysis, writing, coding, review
- Assign a priority order

### Step 2: Worker Assignment
For each sub-task, determine the best worker:
- **Research tasks**: use search_web + firecrawl
- **Analysis tasks**: use RunPython + data-analysis skill
- **Writing tasks**: use docwriter + report-generator skill
- **Coding tasks**: use context skill + code-review skill
- **Review tasks**: use fact-checker skill + code-review skill

If sub-agents are available (TeamCreate), create specialized workers.

### Step 3: Parallel Execution
Dispatch independent sub-tasks in parallel:
- Use TeamSay to communicate with sub-agents
- Monitor progress and handle timeouts
- On failure: retry once, then reassign or skip

### Step 4: Result Aggregation
Combine worker outputs:
- Resolve conflicts (duplicate findings, contradictory conclusions)
- Fill gaps (missing data, skipped sub-tasks)
- Format into a unified output (report, code, document)

### Step 5: Delivery
Present the aggregated result with:
- Summary of what each worker contributed
- Any conflicts or gaps flagged
- Final output file or message

## Quality Rules
- Only parallelize truly independent sub-tasks
- Set a timeout for each worker (default 5 minutes)
- If a worker fails, the orchestrator must continue with remaining workers
- Always flag aggregated results that came from partial failures