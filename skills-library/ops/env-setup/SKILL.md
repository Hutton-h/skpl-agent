---
name: env-setup
description: Environment setup workflow — helps configure development environments, install dependencies, and troubleshoot setup issues.
version: 1.0.0
category: ops
when_to_use: User needs help setting up a development environment, installing dependencies, or troubleshooting environment issues.
---
# Environment Setup Skill — 环境配置

## Goal
Help the user configure and troubleshoot their development environment.

## Available Tools
RunPython, Read, Grep, Glob.

## Workflow

### Step 1: Environment Audit
- Check installed tools: Python, Node.js, Git, Docker
- Verify versions and compatibility
- Identify missing dependencies

### Step 2: Setup Guide
- Provide step-by-step installation instructions
- Configure environment variables
- Install project dependencies

### Step 3: Verification
- Run setup verification commands
- Check that all services can start
- Report any remaining issues

### Step 4: Troubleshooting
- Diagnose common setup issues
- Suggest fixes for version conflicts
- Provide workarounds for platform-specific problems

## Quality Rules
- Always check tool versions before suggesting installation
- Provide platform-specific instructions (Windows/macOS/Linux)
- Include verification steps after each setup step
- Never suggest `sudo` without explaining the risks
