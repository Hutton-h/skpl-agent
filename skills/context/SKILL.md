---
name: context
description: Project context management skill — scan codebase anatomy, track bugs, analyze token usage, and inject contextual information into agent sessions.
version: 1.0.0
category: system
when_to_use: The session needs project awareness — scanning a codebase's symbol structure, recording or listing bugs, analyzing token usage, or injecting relevant code context into the agent prompt.
---

# Context Skill

Provides deep project awareness for SKPL Agent sessions through:

1. **Anatomy Scanner** — Index codebase symbols (functions, classes, imports) using Tree-sitter
2. **Bug Tracker** — Record, deduplicate, and manage bugs with fingerprint-based grouping
3. **Token Analyzer** — Track token usage per model, detect waste patterns
4. **Context Injector** — Inject relevant code context into agent prompts

## Tools

| Tool | Description |
|------|-------------|
| `scan_project` | Scan a project directory for code symbols |
| `report_bug` | Record a bug with fingerprint deduplication |
| `list_bugs` | List bugs for a session |
| `update_bug` | Update bug status |
| `analyze_tokens` | Analyze token usage patterns |
| `inject_context` | Inject relevant context into session |