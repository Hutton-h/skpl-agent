---
name: debug-assistant
description: Debugging assistant workflow — analyzes error logs, stack traces, and code to identify root causes and suggest fixes.
version: 1.0.0
category: coding
when_to_use: User reports a bug, shares an error message, asks for help debugging, or wants to understand why code is failing.
---
# Debug Assistant Skill — 调试助手

## Goal
From an error message or bug description → identify root cause → suggest concrete fix → verify the fix.

## Available Tools
Read, Grep, Glob, RunPython, Write.

## Workflow

### Step 1: Error Analysis
- Parse the error message and stack trace
- Identify the failing line and the call chain
- Classify the error: syntax, runtime, logic, dependency, configuration

### Step 2: Root Cause Investigation
- Read the relevant code files
- Trace the data flow leading to the error
- Check for common patterns: null/undefined, race conditions, type mismatches

### Step 3: Fix Proposal
- Suggest a concrete code change
- Explain why the fix works
- Note any side effects or related changes needed

### Step 4: Verification
- Apply the fix (Write)
- Run the code to verify (if possible)
- Report the result

## Quality Rules
- Never suggest fixes without understanding the root cause
- Explain the "why" behind every fix suggestion
- Flag when a fix is a workaround vs. a proper solution
- Consider the broader impact of the change
