---
name: code-generator
description: Code generation workflow — creates complete code files from natural language descriptions.
version: 1.0.0
category: coding
when_to_use: User asks to generate code, create a script, build a component, or implement a feature.
---
# Code Generator Skill — 代码生成

## Goal
From a natural language description → generate complete, working code files with proper structure, error handling, and documentation.

## Available Tools
Write, RunPython, Read, Grep.

## Workflow

### Step 1: Requirement Analysis
- Parse the user's request for language, framework, and constraints
- Identify required files and their dependencies
- Check existing codebase for conventions (Read/Grep)

### Step 2: Code Generation
- Generate well-structured code with:
  - Proper imports and dependencies
  - Error handling and edge cases
  - Type hints / JSDoc where applicable
  - Inline documentation for complex logic
- Follow project conventions and naming

### Step 3: Testing
- If possible, generate a simple test
- Verify the code compiles/parses

### Step 4: Delivery
- Write files to the appropriate location
- Summarize what was created and how to use it

## Quality Rules
- Never generate code that has security vulnerabilities
- Follow existing project conventions (indentation, naming, structure)
- Include error handling for all I/O and network operations
- Prefer standard library over external dependencies
