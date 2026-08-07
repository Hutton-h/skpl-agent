---
name: git-assistant
description: Git workflow assistant — helps with commits, branches, merges, and PR descriptions.
version: 1.0.0
category: coding
when_to_use: User asks for git help, wants to commit, create a branch, resolve conflicts, or write a PR description.
---
# Git Assistant Skill — Git 助手

## Goal
Help the user with git operations: commit messages, branch management, PR descriptions, and conflict resolution.

## Available Tools
RunPython, Read, Grep.

## Workflow

### Step 1: Context Gathering
- Check current branch and status
- Review staged/unstaged changes
- Understand the purpose of the changes

### Step 2: Action Execution
- **Commit**: Generate a conventional commit message
- **Branch**: Suggest and create appropriately named branches
- **PR**: Generate a structured PR description with changes, testing, and screenshots
- **Conflict**: Analyze conflicts and suggest resolution strategies

### Step 3: Best Practices
- Enforce conventional commit format
- Suggest branch naming conventions
- Review for sensitive files before committing

## Quality Rules
- Commit messages must follow conventional commits
- Never commit secrets or large binary files
- PR descriptions must include what changed, why, and how to test
