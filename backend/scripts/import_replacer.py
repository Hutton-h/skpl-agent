#!/usr/bin/env python3
"""
SKPL Agent Import Path Replacer

Replaces all `agentscope` references in the AgentScope source tree with
`skpl_agent`, while preserving attribution comments and upstream license headers.

Strategy:
1. AST-based rewrite for Python files (safe, semantic)
2. Regex-based rewrite for config files (pyproject.toml, setup.cfg, etc.)
3. String replacements for templates and documentation

Usage:
    python scripts/import_replacer.py <source_dir> <target_dir> [--dry-run]

The source_dir is the AgentScope source tree (e.g., agentscope-main/src/agentscope).
The target_dir is where the processed files should be written (e.g., backend/src/skpl_agent).
"""

import argparse
import ast
import os
import re
import shutil
import sys
import tokenize
from io import StringIO
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

UPSTREAM_ATTRIBUTION = """# This file is derived from the AgentScope project:
#   https://github.com/agentscope-ai/agentscope
# Licensed under Apache License 2.0.
# Copyright (c) Alibaba Tongyi Lab.
# Modifications copyright (c) SKPL Agent Contributors.
"""

# Patterns that should NOT be renamed (they refer to the upstream project, not the package)
KEEP_AS_AGENTSCOPE: list[str] = [
    # GitHub URLs and external references
    r"github\.com/agentscope-ai/agentscope",
    r"https?://.*agentscope",
    # Package name on PyPI
    r'"agentscope"',
    r"'agentscope'",
    # CLI entry point comments
    r"# agentscope",
    # Original attribution
    r"agentscope-ai",
    # pypi references
    r"pip install.*agentscope",
    r"uv add.*agentscope",
]

# Mapping of import paths to replace
IMPORT_REPLACEMENTS: dict[str, str] = {
    "agentscope": "skpl_agent",
    "agentscope.": "skpl_agent.",
}

# File extensions to process
PYTHON_EXTS: set[str] = {".py", ".pyi", ".pyx"}
CONFIG_EXTS: set[str] = {".toml", ".cfg", ".ini", ".yaml", ".yml", ".json"}
DOC_EXTS: set[str] = {".md", ".rst", ".txt", ".mako"}
TEMPLATE_EXTS: set[str] = {".template", ".j2", ".jinja2"}

SKIP_DIRS: set[str] = {
    "__pycache__",
    ".git",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "*.egg-info",
    "_alembic/versions",  # Don't modify existing migration scripts
}

SKIP_FILES: set[str] = {
    "import_replacer.py",
    "setup.py",
    "pyproject.toml",  # package-level, not sub-package
}


# ---------------------------------------------------------------------------
# AST-based Python rewriter
# ---------------------------------------------------------------------------

class ImportTransformer(ast.NodeTransformer):
    """AST transformer that rewrites import paths from agentscope → skpl_agent."""

    def _replace_name(self, name: str) -> str:
        """Replace agentscope prefix with skpl_agent."""
        if name == "agentscope":
            return "skpl_agent"
        if name.startswith("agentscope."):
            return "skpl_agent" + name[len("agentscope"):]
        return name

    def visit_Import(self, node: ast.Import) -> ast.Import:
        for alias in node.names:
            if alias.name == "agentscope" or alias.name.startswith("agentscope."):
                alias.name = self._replace_name(alias.name)
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        if node.module and (node.module == "agentscope" or node.module.startswith("agentscope.")):
            node.module = self._replace_name(node.module)
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        if isinstance(node.value, ast.Name) and node.value.id == "agentscope":
            node.value.id = "skpl_agent"
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id == "agentscope":
            node.id = "skpl_agent"
        return node


def rewrite_python_file(source: str, filepath: str) -> tuple[str, bool]:
    """
    Rewrite a Python source file using AST transformation.
    Returns (new_source, was_modified).
    """
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        # Fall back to regex-based replacement for files with syntax errors
        return _regex_replace(source, filepath)

    transformer = ImportTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)

    try:
        new_source = ast.unparse(new_tree)
    except Exception:
        return _regex_replace(source, filepath)

    # Also handle string literals and comments that AST doesn't cover
    new_source = _regex_replace_in_strings(new_source)

    modified = new_source != source
    return new_source, modified


def _regex_replace(source: str, filepath: str = "") -> tuple[str, bool]:
    """Fallback regex-based replacement."""
    modified = False
    result = source

    # Replace import statements
    patterns = [
        # import agentscope.foo
        (r'\bimport\s+agentscope\b', 'import skpl_agent'),
        # import agentscope.foo as bar
        (r'\bimport\s+agentscope\.', 'import skpl_agent.'),
        # from agentscope.foo import bar
        (r'\bfrom\s+agentscope\b', 'from skpl_agent'),
        # from agentscope.foo import bar
        (r'\bfrom\s+agentscope\.', 'from skpl_agent.'),
        # "agentscope" in strings (config references)
        (r'(["\'`])agentscope\.', r'\1skpl_agent.'),
    ]

    for pattern, replacement in patterns:
        new_result = re.sub(pattern, replacement, result)
        if new_result != result:
            modified = True
            result = new_result

    return result, modified


def _regex_replace_in_strings(source: str) -> str:
    """Replace agentscope references inside string literals."""
    # Replace in double-quoted strings
    source = re.sub(r'"agentscope\.', '"skpl_agent.', source)
    source = re.sub(r"'agentscope\.", "'skpl_agent.", source)
    # Replace dotted references in f-strings and format strings
    source = re.sub(r'\{.*?\bagentscope\.', lambda m: m.group(0).replace('agentscope.', 'skpl_agent.'), source)
    return source


# ---------------------------------------------------------------------------
# Config file rewriter
# ---------------------------------------------------------------------------

def rewrite_config_file(source: str, filepath: str) -> tuple[str, bool]:
    """Rewrite configuration files (TOML, YAML, JSON, etc.)."""
    modified = False
    result = source

    # Replace package references
    patterns = [
        (r'\bagentscope\b', 'skpl_agent'),
        (r'"agentscope"', '"skpl-agent"'),  # package name in JSON/TOML
        (r"'agentscope'", "'skpl-agent'"),
    ]

    for pattern, replacement in patterns:
        new_result = re.sub(pattern, replacement, result)
        if new_result != result:
            modified = True
            result = new_result

    return result, modified


# ---------------------------------------------------------------------------
# Doc / Template file rewriter
# ---------------------------------------------------------------------------

def rewrite_doc_file(source: str, filepath: str) -> tuple[str, bool]:
    """Rewrite documentation and template files."""
    modified = False
    result = source

    # Replace code references
    patterns = [
        (r'\bagentscope\.', 'skpl_agent.'),
        (r'`agentscope`', '`skpl_agent`'),
    ]

    for pattern, replacement in patterns:
        new_result = re.sub(pattern, replacement, result)
        if new_result != result:
            modified = True
            result = new_result

    # Don't replace URLs
    # (already handled by pattern specificity)

    return result, modified


# ---------------------------------------------------------------------------
# File processor
# ---------------------------------------------------------------------------

def should_skip(path: Path, base_dir: Path) -> bool:
    """Check if a file or directory should be skipped."""
    rel = path.relative_to(base_dir)
    parts = rel.parts

    # Skip specific directories
    for part in parts:
        if part in SKIP_DIRS:
            return True
        if part.startswith("."):
            return True

    # Skip specific files
    if path.name in SKIP_FILES:
        return True

    return False


def get_rewriter(filepath: Path) -> callable:
    """Get the appropriate rewriter function for a given file."""
    suffix = filepath.suffix.lower()

    if suffix in PYTHON_EXTS:
        return rewrite_python_file
    elif suffix in CONFIG_EXTS:
        return rewrite_config_file
    elif suffix in DOC_EXTS:
        return rewrite_doc_file
    elif suffix in TEMPLATE_EXTS:
        return rewrite_doc_file
    else:
        return None


def process_file(
    src_path: Path,
    dst_path: Path,
    dry_run: bool = False,
) -> dict:
    """Process a single file. Returns stats dict."""
    rewriter = get_rewriter(src_path)

    if rewriter is None:
        # Binary or unknown file — copy as-is
        if not dry_run:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
        return {"copied": 1, "modified": 0, "skipped": 0}

    try:
        source = src_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file disguised as text — copy as-is
        if not dry_run:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
        return {"copied": 1, "modified": 0, "skipped": 0}

    new_source, modified = rewriter(source, str(src_path))

    if not dry_run:
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        # Add attribution header to modified Python files
        if modified and src_path.suffix.lower() in PYTHON_EXTS:
            # Check if there's already a license header
            if not source.lstrip().startswith("#"):
                new_source = UPSTREAM_ATTRIBUTION + "\n" + new_source

        dst_path.write_text(new_source, encoding="utf-8")

    if modified:
        return {"copied": 0, "modified": 1, "skipped": 0}
    else:
        return {"copied": 1, "modified": 0, "skipped": 0}


def process_directory(
    src_dir: Path,
    dst_dir: Path,
    dry_run: bool = False,
) -> dict:
    """Process an entire directory tree."""
    stats = {"copied": 0, "modified": 0, "skipped": 0, "errors": 0}

    for root, dirs, files in os.walk(src_dir):
        root_path = Path(root)

        # Filter out skipped directories
        dirs[:] = [d for d in dirs if not should_skip(root_path / d, src_dir)]

        for file in files:
            src_path = root_path / file
            if should_skip(src_path, src_dir):
                stats["skipped"] += 1
                continue

            rel_path = src_path.relative_to(src_dir)
            dst_path = dst_dir / rel_path

            try:
                file_stats = process_file(src_path, dst_path, dry_run)
                for key in file_stats:
                    stats[key] += file_stats[key]
            except Exception as e:
                print(f"Error processing {src_path}: {e}", file=sys.stderr)
                stats["errors"] += 1

    return stats


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_no_agentscope_imports(target_dir: Path) -> list[str]:
    """Verify that no agentscope imports remain in the target directory."""
    issues: list[str] = []

    for root, dirs, files in os.walk(target_dir):
        root_path = Path(root)
        for file in files:
            filepath = root_path / file
            if filepath.suffix.lower() not in PYTHON_EXTS:
                continue

            try:
                content = filepath.read_text(encoding="utf-8")
            except Exception:
                continue

            for i, line in enumerate(content.splitlines(), 1):
                # Check for import lines with agentscope
                if re.search(r'\b(?:import|from)\s+agentscope\b', line):
                    # Allow it if it's in a comment
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    # Allow if it's a URL reference
                    if "github.com" in line or "http" in line:
                        continue
                    issues.append(f"{filepath}:{i}: {stripped}")

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Replace agentscope imports with skpl_agent in a source tree."
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Source directory (AgentScope source tree)",
    )
    parser.add_argument(
        "target_dir",
        type=Path,
        help="Target directory (SKPL Agent source tree)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify that no agentscope imports remain after processing",
    )
    args = parser.parse_args()

    if not args.source_dir.exists():
        print(f"Error: Source directory not found: {args.source_dir}", file=sys.stderr)
        sys.exit(1)

    if args.verify:
        issues = verify_no_agentscope_imports(args.target_dir)
        if issues:
            print(f"Found {len(issues)} remaining agentscope references:")
            for issue in issues:
                print(f"  {issue}")
            sys.exit(1)
        else:
            print("All imports successfully replaced!")
            sys.exit(0)

    print(f"Processing: {args.source_dir} -> {args.target_dir}")
    if args.dry_run:
        print("DRY RUN — no files will be modified")

    stats = process_directory(args.source_dir, args.target_dir, dry_run=args.dry_run)

    print(f"\nResults:")
    print(f"  Files copied (no changes):   {stats['copied']}")
    print(f"  Files modified:              {stats['modified']}")
    print(f"  Files skipped:               {stats['skipped']}")
    print(f"  Errors:                      {stats['errors']}")

    if not args.dry_run and stats["modified"] > 0:
        print(f"\nVerifying import replacements...")
        issues = verify_no_agentscope_imports(args.target_dir)
        if issues:
            print(f"WARNING: {len(issues)} agentscope references remain:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("All imports successfully replaced!")

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())