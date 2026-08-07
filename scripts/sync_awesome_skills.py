#!/usr/bin/env python3
"""Sync awesome-llm-apps skills into the SKPL skills-library.

Scans an awesome-list repository (or a local directory of skill descriptions)
and converts entries into SKILL.md files with proper YAML frontmatter,
placing them into ``skills-library/{category}/{skill_name}/``.

Usage:
    python sync_awesome_skills.py \
        --source ./awesome-llm-apps \
        --target ./skills-library \
        --dry-run

    python sync_awesome_skills.py \
        --source ./awesome-llm-apps \
        --target ./skills-library \
        --category coding

Supports three source formats:
    1. Awesome-list markdown (``* [name](url) - description``)
    2. JSON skill manifest (``[{name, description, category, ...}]``)
    3. Directory of SKILL.md files (copied directly)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import frontmatter

# ── YAML frontmatter template ──────────────────────────────────────────────

SKILL_TEMPLATE = """---
name: {name}
description: {description}
version: "1.0.0"
category: {category}
when_to_use: {when_to_use}
---

# {name}

{description}

## Workflow

1. **Analyze** the user's request to confirm this skill is applicable.
2. **Execute** the core task using the appropriate tools.
3. **Deliver** results in the format the user expects.

## Tools

- Use the standard tool set available to all agents.
- Prefer `publish_visual` for presenting structured data (charts, comparisons, dashboards).
- Use `RunPython` for data processing and file generation.

## Output

- Present results clearly and concisely.
- Use visual components when presenting comparisons or metrics.
- Include a summary of what was accomplished.
"""


# ── Category mapping ───────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "coding": ["code", "programming", "debug", "refactor", "test", "git", "dependency", "review", "generate", "cleanup"],
    "research": ["research", "analyze", "market", "trend", "competitor", "fact", "deep", "supply", "sizing"],
    "sales": ["sales", "customer", "lead", "outreach", "meeting", "playbook", "intelligence", "enrichment"],
    "productivity": ["email", "report", "presentation", "social", "document", "doc", "composer", "builder", "generator"],
    "automation": ["automation", "notify", "schedule", "orchestrate", "browser", "whatsapp", "workflow"],
    "content": ["content", "rewrite", "strategy", "blog", "article", "copy"],
    "data": ["data", "analysis", "financial", "survey", "statistics", "spreadsheet"],
    "ops": ["deploy", "audit", "setup", "environment", "website", "monitor", "weekly"],
    "seo": ["seo", "keyword", "geo", "optimization", "search"],
}


def infer_category(name: str, description: str = "") -> str:
    """Infer the skill category from its name and description."""
    text = f"{name} {description}".lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)



def infer_when_to_use(name: str, category: str) -> str:
    """Generate a when_to_use string from the skill name and category."""
    triggers = {
        "coding": "When the user asks to write, review, debug, refactor, or test code",
        "research": "When the user asks to research, analyze, or investigate a topic",
        "sales": "When the user asks about customer development, sales, or outreach",
        "productivity": "When the user asks to create documents, emails, presentations, or reports",
        "automation": "When the user asks to automate a workflow, schedule tasks, or notify",
        "content": "When the user asks to create, rewrite, or strategize content",
        "data": "When the user asks to analyze data, run financial analysis, or process surveys",
        "ops": "When the user asks to deploy, audit, setup, or monitor systems",
        "seo": "When the user asks about SEO, keyword research, or search optimization",
        "general": "When the user asks for help with this specific task",
    }
    return triggers.get(category, triggers["general"])


# ── Source parsers ─────────────────────────────────────────────────────────

def parse_awesome_markdown(source_path: str) -> list[dict]:
    """Parse an awesome-list style markdown file.

    Expected format:
        ## Category Name
        * [Skill Name](url) - Description of the skill
        * [Another Skill](url) - Another description
    """
    skills = []
    current_category = "general"

    with open(source_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Detect category headers
            if line.startswith("## "):
                raw = line[3:].strip().lower()
                # Map common category names
                cat_map = {
                    "coding": "coding", "code": "coding", "development": "coding",
                    "research": "research", "analysis": "research",
                    "sales": "sales", "business": "sales",
                    "productivity": "productivity", "office": "productivity",
                    "automation": "automation", "workflow": "automation",
                    "content": "content", "writing": "content",
                    "data": "data", "analytics": "data",
                    "ops": "ops", "operations": "ops", "devops": "ops",
                    "seo": "seo", "marketing": "seo",
                }
                current_category = cat_map.get(raw, "general")
                continue

            # Parse skill entries
            match = re.match(r'\*\s*\[([^\]]+)\]\([^)]+\)\s*[-–—]\s*(.+)', line)
            if match:
                name = match.group(1).strip()
                description = match.group(2).strip()
                if not infer_category(name, description):
                    category = current_category
                else:
                    category = infer_category(name, description)
                skills.append({
                    "name": name,
                    "description": description,
                    "category": category,
                    "when_to_use": infer_when_to_use(name, category),
                })

    return skills


def parse_json_manifest(source_path: str) -> list[dict]:
    """Parse a JSON skill manifest file.

    Expected format:
        [
            {"name": "Skill Name", "description": "...", "category": "coding", "when_to_use": "..."},
            ...
        ]
    """
    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON manifest must be a list of skill objects")
    for item in data:
        if "name" not in item:
            raise ValueError(f"Missing 'name' field in skill: {item}")
        item.setdefault("category", infer_category(item["name"], item.get("description", "")))
        item.setdefault("when_to_use", infer_when_to_use(item["name"], item["category"]))
    return data


def copy_skill_directories(source_path: str) -> list[dict]:
    """Copy existing SKILL.md directories into the skills-library."""
    skills = []
    for root, dirs, files in os.walk(source_path):
        if "SKILL.md" in files:
            skill_md = os.path.join(root, "SKILL.md")
            try:
                with open(skill_md, encoding="utf-8") as f:
                    meta = frontmatter.loads(f.read())
            except Exception:
                continue
            skills.append({
                "name": meta.get("name", os.path.basename(root)),
                "description": meta.get("description", ""),
                "category": meta.get("category", "general"),
                "when_to_use": meta.get("when_to_use", ""),
                "source_dir": root,
            })
    return skills


# ── Main sync logic ────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert a skill name to a directory-safe slug."""
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def sync_skills(
    skills: list[dict],
    target_dir: str,
    *,
    category_filter: Optional[str] = None,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """Sync skills into the skills-library directory.

    Returns:
        (created, updated, skipped)
    """
    created = 0
    updated = 0
    skipped = 0

    for skill in skills:
        category = skill["category"]
        if category_filter and category != category_filter:
            continue

        name = skill["name"]
        slug = slugify(name)
        skill_dir = os.path.join(target_dir, category, slug)
        skill_md_path = os.path.join(skill_dir, "SKILL.md")

        if dry_run:
            if os.path.isfile(skill_md_path):
                print(f"  [UPDATE] {category}/{slug}")
                updated += 1
            else:
                print(f"  [CREATE] {category}/{slug}")
                created += 1
            continue

        # Generate SKILL.md content
        content = SKILL_TEMPLATE.format(
            name=name,
            description=skill.get("description", ""),
            category=category,
            when_to_use=skill.get("when_to_use", ""),
        )

        # Write to disk
        os.makedirs(skill_dir, exist_ok=True)
        existed = os.path.isfile(skill_md_path)
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(content)

        if existed:
            print(f"  [UPDATED] {category}/{slug}")
            updated += 1
        else:
            print(f"  [CREATED] {category}/{slug}")
            created += 1

    return created, updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync awesome-list skills into the SKPL skills-library",
    )
    parser.add_argument(
        "--source", required=True,
        help="Path to awesome-list repo, JSON manifest, or SKILL.md directory",
    )
    parser.add_argument(
        "--target", default="./skills-library",
        help="Path to the skills-library directory (default: ./skills-library)",
    )
    parser.add_argument(
        "--format", choices=["awesome", "json", "directory"], default="awesome",
        help="Source format: awesome (markdown), json (manifest), or directory (SKILL.md files)",
    )
    parser.add_argument(
        "--category", default=None,
        help="Only sync skills matching this category",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing files",
    )
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    target = os.path.abspath(args.target)

    if not os.path.exists(source):
        print(f"Error: source path does not exist: {source}", file=sys.stderr)
        sys.exit(1)

    print(f"Source: {source}")
    print(f"Target: {target}")
    print(f"Format: {args.format}")
    if args.dry_run:
        print("Mode: DRY RUN (no files will be written)")
    print()

    # Parse source
    if args.format == "awesome":
        skills = parse_awesome_markdown(source)
    elif args.format == "json":
        skills = parse_json_manifest(source)
    elif args.format == "directory":
        skills = copy_skill_directories(source)
    else:
        print(f"Error: unknown format '{args.format}'", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(skills)} skills")
    print()

    created, updated, skipped = sync_skills(
        skills, target,
        category_filter=args.category,
        dry_run=args.dry_run,
    )

    print()
    print(f"Summary: {created} created, {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    main()
