---
name: test-generator
description: Test generation workflow — creates unit tests, integration tests, and test fixtures for existing code.
version: 1.0.0
category: coding
when_to_use: User asks to write tests, add test coverage, or create test cases for existing code.
---
# Test Generator Skill — 测试生成

## Goal
From existing code → generate comprehensive test coverage with unit tests, edge cases, and mocks.

## Available Tools
Read, Grep, Glob, RunPython, Write.

## Workflow

### Step 1: Code Understanding
- Read the target file(s) to understand the API surface
- Identify all public functions, methods, and classes
- Note dependencies that need mocking

### Step 2: Test Strategy
- Determine test framework (based on project conventions)
- Plan coverage: happy path, edge cases, error handling
- Identify test fixtures needed

### Step 3: Test Generation
- Write unit tests for each public function
- Include edge cases: empty input, None, large values, boundary values
- Mock external dependencies
- Test error handling paths

### Step 4: Verification
- Run the tests (if possible)
- Report coverage gaps

## Quality Rules
- Tests must be independently runnable
- One test per behavior, not one per function
- Use descriptive test names that explain the scenario
- Never skip tests — use expectedFailure for known issues
