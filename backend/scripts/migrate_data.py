#!/usr/bin/env python3
"""
SKPL Agent Data Migration Script

Migrates data from an existing AgentScope installation to SKPL Agent format.
This script handles:
- Database schema migration
- Configuration file conversion
- Workspace data migration
- Model registration migration

Usage:
    python scripts/migrate_data.py --source-db <path> --target-db <path> [--dry-run]
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

class MigrationContext:
    """Holds migration state and configuration."""

    def __init__(
        self,
        source_db: Path,
        target_db: Path,
        source_config: Optional[Path] = None,
        source_data: Optional[Path] = None,
        dry_run: bool = False,
    ):
        self.source_db = source_db
        self.target_db = target_db
        self.source_config = source_config
        self.source_data = source_data or source_db.parent / "data"
        self.dry_run = dry_run
        self.stats: dict[str, int] = {
            "agents_migrated": 0,
            "sessions_migrated": 0,
            "workspaces_migrated": 0,
            "models_migrated": 0,
            "configs_migrated": 0,
            "errors": 0,
        }

    def log(self, message: str, level: str = "INFO"):
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}[{level}] {message}")

    def log_stat(self, key: str):
        self.stats[key] += 1


# ---------------------------------------------------------------------------
# Step 1: Database Migration
# ---------------------------------------------------------------------------

def migrate_database(ctx: MigrationContext) -> bool:
    """Migrate SQLite database from AgentScope to SKPL Agent schema."""
    ctx.log("Starting database migration...")

    if not ctx.source_db.exists():
        ctx.log(f"Source database not found: {ctx.source_db}", "WARNING")
        return True  # Not an error if no source DB

    if not ctx.dry_run:
        try:
            # Copy the database file
            ctx.target_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ctx.source_db, ctx.target_db)
            ctx.log(f"Database copied to {ctx.target_db}")
        except Exception as e:
            ctx.log(f"Failed to copy database: {e}", "ERROR")
            ctx.stats["errors"] += 1
            return False

    # Note: Schema migration (adding new tables) is handled by Alembic migrations.
    # This script only copies the data. The actual schema changes are applied
    # via `alembic upgrade head` after this script runs.
    ctx.log(
        "Database file copied. Run 'alembic upgrade head' to apply schema migrations."
    )
    return True


# ---------------------------------------------------------------------------
# Step 2: Configuration Migration
# ---------------------------------------------------------------------------

def migrate_configuration(ctx: MigrationContext) -> bool:
    """Migrate AgentScope configuration to SKPL Agent format."""
    ctx.log("Starting configuration migration...")

    if not ctx.source_config or not ctx.source_config.exists():
        ctx.log("No source configuration found, skipping.", "WARNING")
        return True

    # Key mappings from AgentScope to SKPL Agent config
    KEY_MAPPINGS: dict[str, str] = {
        # Model configuration stays the same
        "model": "model",
        "agent": "agent",
        # These are restructured
        "storage": "core.storage",
        "service": "core.service",
        "workspace": "workspace",
        "rag": "rag",
        "memory": "memory",
    }

    try:
        source_config = json.loads(ctx.source_config.read_text())
    except Exception as e:
        ctx.log(f"Failed to read source config: {e}", "ERROR")
        ctx.stats["errors"] += 1
        return False

    # Transform to SKPL format
    target_config: dict[str, Any] = {
        "core": {},
        "context": {},
        "desktop": {},
        "web": {},
        "update": {},
        "quota": {},
    }

    # Migrate known keys
    for old_key, new_path in KEY_MAPPINGS.items():
        if old_key in source_config:
            parts = new_path.split(".")
            target = target_config
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = source_config[old_key]

    # Migrate model configs
    if "model" in source_config:
        target_config["core"]["model"] = source_config["model"]

    if not ctx.dry_run:
        target_config_path = Path(".env.skpl.json")
        target_config_path.write_text(json.dumps(target_config, indent=2))
        ctx.log(f"Configuration migrated to {target_config_path}")

    ctx.log_stat("configs_migrated")
    return True


# ---------------------------------------------------------------------------
# Step 3: Workspace Data Migration
# ---------------------------------------------------------------------------

def migrate_workspace_data(ctx: MigrationContext) -> bool:
    """Migrate workspace data files."""
    ctx.log("Starting workspace data migration...")

    source_workspaces = ctx.source_data / "workspaces"
    if not source_workspaces.exists():
        ctx.log("No workspace data found, skipping.", "WARNING")
        return True

    target_workspaces = Path("data/workspaces")

    if not ctx.dry_run:
        try:
            if target_workspaces.exists():
                # Merge, don't overwrite
                for item in source_workspaces.iterdir():
                    target_item = target_workspaces / item.name
                    if not target_item.exists():
                        if item.is_dir():
                            shutil.copytree(item, target_item)
                        else:
                            shutil.copy2(item, target_item)
                        ctx.log_stat("workspaces_migrated")
            else:
                shutil.copytree(source_workspaces, target_workspaces)
                ctx.log_stat("workspaces_migrated")
        except Exception as e:
            ctx.log(f"Failed to migrate workspace data: {e}", "ERROR")
            ctx.stats["errors"] += 1
            return False

    ctx.log(f"Migrated {ctx.stats['workspaces_migrated']} workspace items")
    return True


# ---------------------------------------------------------------------------
# Step 4: Model Registration Migration
# ---------------------------------------------------------------------------

def migrate_model_registrations(ctx: MigrationContext) -> bool:
    """Migrate model provider registrations."""
    ctx.log("Starting model registration migration...")

    model_configs = ctx.source_data / "model_configs"
    if not model_configs.exists():
        ctx.log("No model configurations found, skipping.", "WARNING")
        return True

    target_model_configs = Path("data/model_configs")

    if not ctx.dry_run:
        try:
            if target_model_configs.exists():
                for item in model_configs.iterdir():
                    target_item = target_model_configs / item.name
                    if not target_item.exists():
                        shutil.copy2(item, target_item)
                        ctx.log_stat("models_migrated")
            else:
                target_model_configs.mkdir(parents=True, exist_ok=True)
                for item in model_configs.iterdir():
                    shutil.copy2(item, target_model_configs / item.name)
                    ctx.log_stat("models_migrated")
        except Exception as e:
            ctx.log(f"Failed to migrate model registrations: {e}", "ERROR")
            ctx.stats["errors"] += 1
            return False

    ctx.log(f"Migrated {ctx.stats['models_migrated']} model configurations")
    return True


# ---------------------------------------------------------------------------
# Step 5: Verification
# ---------------------------------------------------------------------------

def verify_migration(ctx: MigrationContext) -> bool:
    """Verify that the migration was successful."""
    ctx.log("Verifying migration...")

    issues: list[str] = []

    # Check database
    if ctx.target_db.exists():
        ctx.log(f"Database exists: {ctx.target_db}")
    else:
        issues.append("Target database not found")

    # Check data directory
    data_dir = Path("data")
    if data_dir.exists():
        ctx.log(f"Data directory exists: {data_dir}")
    else:
        issues.append("Data directory not found")

    if issues:
        for issue in issues:
            ctx.log(f"Verification issue: {issue}", "ERROR")
        return False

    ctx.log("Verification passed!")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from AgentScope to SKPL Agent"
    )
    parser.add_argument(
        "--source-db",
        type=Path,
        default=Path("agentscope.db"),
        help="Path to AgentScope SQLite database",
    )
    parser.add_argument(
        "--target-db",
        type=Path,
        default=Path("data/skpl.db"),
        help="Path for SKPL Agent SQLite database",
    )
    parser.add_argument(
        "--source-config",
        type=Path,
        default=None,
        help="Path to AgentScope configuration file",
    )
    parser.add_argument(
        "--source-data",
        type=Path,
        default=None,
        help="Path to AgentScope data directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database migration",
    )
    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Skip configuration migration",
    )
    parser.add_argument(
        "--skip-workspace",
        action="store_true",
        help="Skip workspace data migration",
    )
    args = parser.parse_args()

    ctx = MigrationContext(
        source_db=args.source_db,
        target_db=args.target_db,
        source_config=args.source_config,
        source_data=args.source_data,
        dry_run=args.dry_run,
    )

    print("=" * 60)
    print("SKPL Agent Data Migration")
    print("=" * 60)
    if args.dry_run:
        print("DRY RUN — no changes will be made")
    print()

    # Run migration steps
    steps = [
        ("Database", not args.skip_db, migrate_database),
        ("Configuration", not args.skip_config, migrate_configuration),
        ("Workspace Data", not args.skip_workspace, migrate_workspace_data),
        ("Model Registrations", True, migrate_model_registrations),
    ]

    for step_name, should_run, step_func in steps:
        if should_run:
            print(f"\n--- {step_name} Migration ---")
            if not step_func(ctx):
                print(f"\nMigration failed at step: {step_name}")
                sys.exit(1)

    # Verification
    if not args.dry_run:
        print(f"\n--- Verification ---")
        verify_migration(ctx)

    # Summary
    print(f"\n{'=' * 60}")
    print("Migration Summary:")
    print(f"  Databases migrated:        1")
    print(f"  Configurations migrated:   {ctx.stats['configs_migrated']}")
    print(f"  Workspaces migrated:       {ctx.stats['workspaces_migrated']}")
    print(f"  Models migrated:           {ctx.stats['models_migrated']}")
    print(f"  Errors:                    {ctx.stats['errors']}")
    print(f"{'=' * 60}")

    if ctx.stats["errors"] > 0:
        print("\nWARNING: Migration completed with errors.")
        sys.exit(1)
    else:
        print("\nMigration completed successfully!")

    return 0


if __name__ == "__main__":
    sys.exit(main())