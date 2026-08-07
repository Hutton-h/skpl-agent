---
name: project-cleanup
description: Project cleanup workflow — detects dead or abandoned projects, analyzes the reason for abandonment, estimates revival effort, and produces a structured cleanup plan with priority ordering.
version: 1.0.0
category: coding
when_to_use: User asks to clean up projects, find dead repositories, audit a project folder for abandoned work, or wants a revival plan for stale projects.
---

# Project Cleanup Skill — 项目清理

## Goal
Scan a directory of projects → classify each as active/stale/dead → analyze abandonment reasons → produce a ranked cleanup/revival plan.

## Available Tools
Glob, Read, Grep, RunPython.

## Workflow

### Step 1: Project Discovery
Use Glob to find project indicators:
- `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`
- `.git/` directories
- `README.md` (to extract project descriptions)

### Step 2: Vitality Scoring (RunPython)
For each project, compute a vitality score from:
- **Last commit date** (via git log or file modification times)
- **Dependency freshness** (outdated packages count)
- **Build health** (does it still install/compile?)
- **README quality** (has a description? setup instructions?)
- **Test presence** (are there tests? do they pass?)

Score 0-100, classify:
- 70+: Active (green)
- 40-69: Stale (yellow)
- 0-39: Dead (red)

### Step 3: Abandonment Analysis
For dead/stale projects, analyze:
- Dependency hell (broken deps)
- Framework rot (deprecated framework version)
- Scope creep (too ambitious)
- Missing knowledge (original author left)
- Superseded (replaced by another project)

### Step 4: Revival Plan
For each candidate project:
- Estimated effort: hours to revive
- Key blockers: what must be fixed first
- Alternatives: existing solutions that could replace it
- Recommendation: revive / archive / delete

### Step 5: Report
Produce a structured report:
- Executive summary with counts by status
- Priority-ordered action list
- Risk assessment (what breaks if we delete?)
- Archive checklist for deletion candidates

## Quality Rules
- Never delete anything — only recommend
- Git history is the best vitality signal; file mtime is a fallback
- Flag projects with no README as high-risk for deletion
- Consider the project's role in the ecosystem (is it a dependency of other projects?)