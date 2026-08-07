---
name: refactor-assistant
description: Refactoring assistant workflow — analyzes code for improvement opportunities and safely refactors while preserving behavior.
version: 1.0.0
category: coding
when_to_use: User asks to refactor code, improve code quality, reduce complexity, or restructure a module.
---
# Refactor Assistant Skill — 重构助手

## Goal
From existing code → identify improvement opportunities → refactor safely → verify behavior is preserved.

## Available Tools
Read, Grep, Glob, Write, RunPython.

## Workflow

### Step 1: Code Analysis
- Read the target code and its dependencies
- Identify: long functions, deep nesting, duplicated code, tight coupling
- Measure complexity (lines, branches, dependencies)

### Step 2: Refactor Plan
- Prioritize: extract functions, reduce nesting, remove duplication
- Plan the refactoring in small, reversible steps
- Each step should be independently verifiable

### Step 3: Safe Refactoring
- Apply one refactoring at a time
- Preserve all existing behavior and interfaces
- Update all callers and references

### Step 4: Verification
- Verify the code still works (run tests if available)
- Compare before/after: lines reduced, complexity reduced
- Report the improvements

## Quality Rules
- Never change behavior during refactoring
- One refactoring per step — never batch unrelated changes
- If tests exist, they must pass after every step
- Flag when a "refactoring" would actually change behavior
