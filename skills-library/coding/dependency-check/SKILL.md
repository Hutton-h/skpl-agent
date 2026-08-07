---
name: dependency-check
description: Dependency health check — scans project dependencies for stdlib conflicts, deprecated packages, version pinning gaps, and known vulnerabilities. Produces a structured report with upgrade recommendations.
version: 1.0.0
category: coding
when_to_use: User asks to check dependencies, audit packages, find deprecated or vulnerable libraries, or wants to pin versions and resolve conflicts.
---

# Dependency Check Skill — 依赖检查

## Goal
Scan a project's dependency manifest → identify stdlib conflicts, deprecated packages, unpinned versions, and known vulnerabilities → produce a fix-ordered report.

## Available Tools
Read, Glob, Grep, RunPython.

## Workflow

### Step 1: Manifest Discovery
Use Glob to find dependency manifests:
- Python: `requirements.txt`, `pyproject.toml`, `Pipfile`
- Node.js: `package.json`
- Rust: `Cargo.toml`
- Go: `go.mod`

### Step 2: Dependency Analysis (RunPython)

For Python projects, run:
```python
import pkg_resources, subprocess, json
# Parse requirements
# Check each package: latest version, deprecation status, known vulns
# Compare with stdlib — flag name-shadowing packages
```

For Node.js projects, run:
```python
import subprocess, json
result = subprocess.run(['npm', 'outdated', '--json'], capture_output=True, text=True)
# Parse and report outdated/deprecated packages
```

### Step 3: Check Categories
- **Stdlib conflicts**: packages that shadow standard library names
- **Deprecated**: packages marked as deprecated by maintainers
- **Unpinned**: version ranges without upper bounds
- **Vulnerabilities**: packages with known CVEs (check against advisory DB)
- **Transitive bloat**: unexpectedly large dependency trees

### Step 4: Report Generation
Produce a structured report:
- Summary table: package, current version, latest version, status
- Risk classification: 🔴 Critical / 🟠 Warning / 🔵 Info
- Upgrade path: ordered list of safe upgrades (respecting compatibility)
- Breaking changes: packages with major version bumps and changelog links

## Quality Rules
- Never suggest upgrading across major versions without checking changelogs
- Flag but don't force pinning of dev dependencies
- Respect lock files — don't suggest changes that would break the lock
- Cross-reference with the project's minimum supported Python/Node version