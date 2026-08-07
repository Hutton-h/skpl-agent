---
name: doc-generator
description: Documentation generation workflow — creates API docs, README files, and inline documentation from code.
version: 1.0.0
category: productivity
when_to_use: User asks to generate documentation, write API docs, create a README, or add docstrings.
---
# Documentation Generator Skill — 文档生成

## Goal
From code → generate comprehensive, well-structured documentation.

## Available Tools
Read, Grep, Glob, Write, RunPython.

## Workflow

### Step 1: Code Understanding
- Read the target files
- Identify public API surface (functions, classes, methods)
- Extract type signatures and docstrings

### Step 2: Documentation Structure
- API reference: function signatures, parameters, return values
- Usage examples: common patterns and edge cases
- Architecture overview: module relationships

### Step 3: Generation
- Write documentation in the requested format (Markdown, HTML, docstrings)
- Include code examples with proper syntax
- Cross-reference related functions and modules

### Step 4: Delivery
- Write the documentation file(s)
- Report the coverage (documented vs. total public API)

## Quality Rules
- Every public function must have a docstring
- Examples must be runnable and correct
- Document edge cases and error conditions
- Keep documentation in sync with the code
