"""Context fallback strategy — degraded context injection when full anatomy is unavailable.

When the anatomy store is empty or a project scan fails, this module provides
a series of fallback strategies to inject useful context into agent sessions
rather than failing silently.

Fallback tiers (tried in order):
1. Cached anatomy from previous sessions (if available)
2. File-system heuristic summary (directory tree, file sizes, last modified)
3. Language-agnostic file-level comments extraction
4. Empty context with a diagnostic note (last resort)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class FallbackContext:
    """Context assembled through fallback mechanisms."""

    source: str  # "cached", "heuristic", "comments", "none"
    summary: str
    file_list: list[str] = field(default_factory=list)
    symbol_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = field(default_factory=list)


@dataclass
class FallbackResult:
    """Result of a fallback context assembly attempt."""

    success: bool
    tier: int  # Which tier succeeded (1-4, 0 = no fallback needed)
    context: FallbackContext | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# File Heuristic Scanner
# ---------------------------------------------------------------------------


class FileHeuristicScanner:
    """Extracts a lightweight summary of a project directory without language-specific parsing.

    Produces a directory tree, file count, and per-file metadata (size, extension,
    last-modified time) that can serve as a minimal context fallback.
    """

    MAX_FILES = 200
    MAX_DEPTH = 4
    IGNORE_PATTERNS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
        "dist", "build", ".next", ".turbo", "target",
        "*.pyc", "*.pyo", "*.egg-info",
    }

    def scan(self, root: Path, max_files: int = MAX_FILES) -> FallbackContext:
        """Scan a directory and produce a heuristic summary.

        Args:
            root: Project root directory.
            max_files: Maximum number of files to include.

        Returns:
            A FallbackContext with file-system level information.
        """
        if not root.is_dir():
            return FallbackContext(
                source="none",
                summary=f"Directory not found: {root}",
            )

        files: list[dict[str, object]] = []
        total_size = 0
        extension_counts: dict[str, int] = {}

        try:
            for entry in root.rglob("*"):
                if entry.is_file():
                    rel_path = entry.relative_to(root)
                    rel_str = str(rel_path)

                    if self._is_ignored(rel_str):
                        continue

                    try:
                        stat = entry.stat()
                        size = stat.st_size
                        mtime = stat.st_mtime
                    except OSError:
                        size = 0
                        mtime = 0.0

                    files.append({
                        "path": rel_str,
                        "size": size,
                        "mtime": mtime,
                    })
                    total_size += size

                    ext = entry.suffix or "(no ext)"
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1

                    if len(files) >= max_files:
                        break
        except Exception:
            logger.exception("Heuristic scan failed for %s", root)
            return FallbackContext(
                source="heuristic",
                summary=f"Scan error while traversing {root}",
                warnings=["Scan encountered an error — partial results may be incomplete"],
            )

        top_extensions = sorted(
            extension_counts.items(), key=lambda x: x[1], reverse=True
        )[:8]

        parts: list[str] = [
            f"Project: {root.name}",
            f"Files scanned: {len(files)}",
            f"Total size: {self._format_size(total_size)}",
            "Top extensions: " + ", ".join(
                f"{ext} ({count})" for ext, count in top_extensions
            ),
        ]

        if len(files) >= max_files:
            parts.append(f"(Limited to {max_files} files — directory may be larger)")

        return FallbackContext(
            source="heuristic",
            summary="\n".join(parts),
            file_list=[f["path"] for f in files],
            symbol_count=0,
        )

    @staticmethod
    def _is_ignored(path: str) -> bool:
        """Check if a path should be ignored."""
        parts = set(Path(path).parts)
        return bool(parts & FileHeuristicScanner.IGNORE_PATTERNS)

    @staticmethod
    def _format_size(size: int) -> str:
        """Format a byte count into a human-readable string."""
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
# Comments Extractor
# ---------------------------------------------------------------------------


class CommentsExtractor:
    """Language-agnostic comment extraction using simple heuristics.

    Extracts the first N lines of comments from source files without
    requiring Tree-sitter or language-specific parsers. Useful as a
    mid-tier fallback when symbol extraction is unavailable.
    """

    COMMENT_PATTERNS: dict[str, tuple[str, str | None]] = {
        # extension: (line_prefix, block_start/end)
        ".py": ("#", '"""'),
        ".ts": ("//", "/*"),
        ".tsx": ("//", "/*"),
        ".js": ("//", "/*"),
        ".jsx": ("//", "/*"),
        ".go": ("//", "/*"),
        ".rs": ("//", "/*"),
        ".java": ("//", "/*"),
        ".c": ("//", "/*"),
        ".cpp": ("//", "/*"),
        ".h": ("//", "/*"),
        ".rb": ("#", "=begin"),
        ".php": ("//", "/*"),
        ".swift": ("//", "/*"),
        ".kt": ("//", "/*"),
        ".sh": ("#", None),
        ".yaml": ("#", None),
        ".yml": ("#", None),
        ".toml": ("#", None),
        ".cfg": ("#", None),
        ".ini": ("#", None),
        ".md": ("<!--", None),
    }

    MAX_COMMENT_LINES = 5
    MAX_FILES = 50

    def extract(self, root: Path, max_files: int = MAX_FILES) -> FallbackContext:
        """Extract leading comments from source files in a directory.

        Args:
            root: Project root directory.
            max_files: Maximum files to process.

        Returns:
            A FallbackContext with extracted comments.
        """
        results: list[str] = []
        files_processed = 0
        warnings: list[str] = []

        try:
            for entry in root.rglob("*"):
                if not entry.is_file():
                    continue
                if files_processed >= max_files:
                    break

                ext = entry.suffix
                if ext not in self.COMMENT_PATTERNS:
                    continue

                rel_path = entry.relative_to(root)
                if self._is_ignored(str(rel_path)):
                    continue

                try:
                    comments = self._extract_from_file(entry)
                    if comments:
                        results.append(f"--- {rel_path} ---\n{comments}")
                        files_processed += 1
                except Exception:
                    logger.debug("Failed to extract comments from %s", rel_path)
        except Exception:
            logger.exception("Comments extraction failed for %s", root)
            warnings.append("Comments extraction encountered an error")

        if not results:
            return FallbackContext(
                source="comments",
                summary="No comments found in project files.",
                warnings=warnings,
            )

        return FallbackContext(
            source="comments",
            summary=f"Extracted leading comments from {files_processed} files.",
            file_list=[r.split("\n")[0].replace("--- ", "").replace(" ---", "")
                      for r in results],
            symbol_count=len(results),
            warnings=warnings,
        )

    def _extract_from_file(self, filepath: Path) -> str:
        """Extract leading comments from a single file."""
        ext = filepath.suffix
        line_prefix, block_delim = self.COMMENT_PATTERNS.get(ext, ("#", None))

        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
        comments: list[str] = []
        in_block = False
        block_delimiter: str | None = None

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if comments:
                    break
                continue

            # Block comment handling
            if block_delim and not in_block:
                if stripped.startswith(block_delim) or stripped.startswith("/*"):
                    in_block = True
                    block_delimiter = block_delim
                    comment_text = stripped[len(block_delim):].strip()
                    # Handle single-line block comments like /* ... */
                    if block_delim == "/*" and "*/" in comment_text:
                        comment_text = comment_text[:comment_text.index("*/")]
                        comments.append(comment_text)
                        in_block = False
                    elif comment_text:
                        comments.append(comment_text)
                    continue

            if in_block:
                if block_delimiter and block_delimiter in stripped:
                    end_idx = stripped.index(block_delimiter)
                    comment_text = stripped[:end_idx].strip()
                    if comment_text:
                        comments.append(comment_text)
                    in_block = False
                    continue
                comments.append(stripped)
                continue

            # Line comment
            if stripped.startswith(line_prefix):
                comment_text = stripped[len(line_prefix):].strip()
                if comment_text:
                    comments.append(comment_text)
            elif comments:
                break

            if len(comments) >= self.MAX_COMMENT_LINES:
                break

        return "\n".join(comments)

    @staticmethod
    def _is_ignored(path: str) -> bool:
        parts = set(Path(path).parts)
        ignore = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", ".turbo", "target",
        }
        return bool(parts & ignore)


# ---------------------------------------------------------------------------
# Fallback Strategy
# ---------------------------------------------------------------------------


class ContextFallbackStrategy:
    """Orchestrates context fallback across multiple tiers.

    Tries each tier in order until one yields usable context:
    1. Cached anatomy (from previous sessions)
    2. Heuristic directory summary
    3. Language-agnostic comment extraction
    4. Empty context with diagnostic note
    """

    def __init__(
        self,
        *,
        enable_cache: bool = True,
        enable_heuristic: bool = True,
        enable_comments: bool = True,
    ) -> None:
        self._enable_cache = enable_cache
        self._enable_heuristic = enable_heuristic
        self._enable_comments = enable_comments
        self._heuristic_scanner = FileHeuristicScanner()
        self._comments_extractor = CommentsExtractor()
        self._cache: dict[str, FallbackContext] = {}

    async def assemble(
        self,
        project_root: Path,
        session_id: str,
    ) -> FallbackResult:
        """Assemble context using the best available fallback tier.

        Args:
            project_root: Path to the project directory.
            session_id: Current session identifier.

        Returns:
            A FallbackResult indicating which tier succeeded and the context.
        """
        # Tier 1: Cached anatomy
        if self._enable_cache and project_root in self._cache:
            cached = self._cache[str(project_root)]
            logger.info(
                "Fallback tier 1 (cached) used for %s [session=%s]",
                project_root, session_id,
            )
            return FallbackResult(
                success=True,
                tier=1,
                context=cached,
            )

        # Tier 2: Heuristic scan
        if self._enable_heuristic:
            try:
                context = self._heuristic_scanner.scan(project_root)
                if context.file_list:
                    self._cache[str(project_root)] = context
                    logger.info(
                        "Fallback tier 2 (heuristic) used for %s [session=%s]",
                        project_root, session_id,
                    )
                    return FallbackResult(
                        success=True,
                        tier=2,
                        context=context,
                    )
            except Exception as exc:
                logger.warning("Heuristic fallback failed: %s", exc)

        # Tier 3: Comment extraction
        if self._enable_comments:
            try:
                context = self._comments_extractor.extract(project_root)
                if context.symbol_count > 0:
                    self._cache[str(project_root)] = context
                    logger.info(
                        "Fallback tier 3 (comments) used for %s [session=%s]",
                        project_root, session_id,
                    )
                    return FallbackResult(
                        success=True,
                        tier=3,
                        context=context,
                    )
            except Exception as exc:
                logger.warning("Comments fallback failed: %s", exc)

        # Tier 4: Empty context (last resort)
        empty = FallbackContext(
            source="none",
            summary=f"No context could be assembled for {project_root.name}. "
                     "The anatomy store is empty and all fallback strategies failed. "
                     "Consider running a manual scan or checking file permissions.",
            warnings=[
                "All context fallback strategies failed",
                "Anatomy store is empty or unavailable",
                "Project may be empty or inaccessible",
            ],
        )
        logger.warning(
            "Fallback tier 4 (empty) used for %s [session=%s]",
            project_root, session_id,
        )
        return FallbackResult(
            success=False,
            tier=4,
            context=empty,
            error="All fallback strategies exhausted",
        )

    def clear_cache(self) -> None:
        """Clear the in-memory fallback cache."""
        self._cache.clear()

    def invalidate_cache(self, project_root: Path) -> None:
        """Remove a specific project from the cache."""
        self._cache.pop(str(project_root), None)


__all__ = [
    "ContextFallbackStrategy",
    "FallbackContext",
    "FallbackResult",
    "FileHeuristicScanner",
    "CommentsExtractor",
]