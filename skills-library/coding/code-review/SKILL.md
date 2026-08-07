---
name: code-review
description: Code review workflow — reads code files, checks for quality issues, security vulnerabilities, and best-practice violations, then produces a structured review report with actionable suggestions.
version: 1.0.0
category: coding
when_to_use: User asks to review code, check code quality, audit for security issues, or wants a code review of a file or project.
---

# Code Review Skill — 代码审查

## Goal
Read code files → analyze for quality/security/best-practices → produce a structured review report with severity levels and actionable fix suggestions.

## Available Tools
Read, Grep, Glob, RunPython.

## Workflow

### Step 1: Scope Discovery
Use Glob and Grep to identify the code files to review:
- If user gives a file path, review that file
- If user gives a directory, find all relevant source files
- Respect .gitignore patterns when available

### Step 2: Multi-Pass Analysis
Read each file and perform layered checks:

**Pass 1 — Security:**
- Hardcoded secrets (API keys, passwords, tokens)
- SQL injection risks (string concatenation in queries)
- XSS vulnerabilities (unsanitized user input in HTML)
- Unsafe deserialization
- Missing authentication/authorization checks

**Pass 2 — Quality:**
- Exception handling gaps (bare except, empty catch)
- Resource leaks (unclosed files, connections, sessions)
- Race conditions (shared mutable state without locks)
- Incorrect error propagation

**Pass 3 — Best Practices:**
- Naming conventions (PEP8 / ESLint / language-specific)
- Function length and complexity
- Missing type hints or JSDoc
- Dead code and unused imports
- Test coverage gaps

### Step 3: Report Generation
Produce a structured report:
- Severity classification: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low
- Each finding: file, line, issue, suggested fix
- Summary statistics (total issues by severity)
- Top 3 recommended actions

## Quality Rules
- Never flag code style if it matches the project's existing conventions
- Distinguish between "must fix" (security/crash) and "nice to have" (style)
- Suggest concrete fixes, not vague advice
- Respect the project's language and framework idioms