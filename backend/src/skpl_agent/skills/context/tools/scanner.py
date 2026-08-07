"""Project scanner — directory structure analysis and file discovery.

Scans project directories to produce a structured overview including
file tree, language statistics, and recent modification tracking.
Respects .gitignore rules for filtering.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Language extension mapping for statistics
_EXTENSION_LANG_MAP: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Bash",
    ".ps1": "PowerShell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".css": "CSS",
    ".scss": "SCSS",
    ".html": "HTML",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

_DEFAULT_EXCLUDE = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".next", ".turbo", ".cache", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "coverage", ".tox", ".eggs",
    "*.egg-info", "*.pyc", "*.pyo", "*.so", "*.dll", "*.dylib",
}


@dataclass
class FileEntry:
    """Metadata for a single scanned file."""

    path: str
    relative_path: str
    language: str = ""
    size_bytes: int = 0
    last_modified: float = 0.0
    extension: str = ""


@dataclass
class ProjectScanResult:
    """Result of a project directory scan.

    Attributes:
        project_path: Root path of the scanned project.
        file_tree: Flat list of discovered file entries.
        language_stats: Count of files per detected language.
        total_files: Total number of files found.
        total_size_bytes: Total size of all files in bytes.
        scan_duration_ms: Time taken to complete the scan.
        error: Error message if the scan failed.
    """

    project_path: str
    file_tree: list[FileEntry] = field(default_factory=list)
    language_stats: dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_size_bytes: int = 0
    scan_duration_ms: float = 0.0
    error: str = ""


class ProjectScanner:
    """Scans project directory structure and produces an overview.

    Supports .gitignore-style filtering and provides language
    statistics together with recent modification data.

    Usage:
        >>> scanner = ProjectScanner()
        >>> result = scanner.scan_project("/path/to/project")
        >>> print(f"Found {result.total_files} files")
        >>> for lang, count in result.language_stats.items():
        >>>     print(f"  {lang}: {count}")
    """

    def __init__(self) -> None:
        self._ignore_patterns: list[str] = []

    # ── Main API ─────────────────────────────────────────────────────────

    def scan_project(self, project_path: str | Path) -> ProjectScanResult:
        """Scan a project directory and return its structure overview.

        Args:
            project_path: Absolute or relative path to the project root.

        Returns:
            ProjectScanResult with file tree, language stats, and metadata.
        """
        start = time.monotonic()
        project_path = Path(project_path).resolve()

        if not project_path.is_dir():
            return ProjectScanResult(
                project_path=str(project_path),
                error=f"Not a directory: {project_path}",
                scan_duration_ms=(time.monotonic() - start) * 1000,
            )

        # Load .gitignore patterns
        self._ignore_patterns = self._load_gitignore(project_path)

        try:
            files: list[FileEntry] = []
            lang_stats: dict[str, int] = {}
            total_size = 0

            for root, dirs, filenames in os.walk(project_path):
                # Filter directories in-place
                dirs[:] = [
                    d for d in dirs
                    if not self._should_ignore(Path(root) / d, project_path)
                ]

                for fname in filenames:
                    file_path = Path(root) / fname
                    if self._should_ignore(file_path, project_path):
                        continue

                    try:
                        stat = file_path.stat()
                    except OSError:
                        continue

                    ext = file_path.suffix.lower()
                    lang = _EXTENSION_LANG_MAP.get(ext, "Other")

                    entry = FileEntry(
                        path=str(file_path),
                        relative_path=str(file_path.relative_to(project_path)),
                        language=lang,
                        size_bytes=stat.st_size,
                        last_modified=stat.st_mtime,
                        extension=ext,
                    )
                    files.append(entry)
                    lang_stats[lang] = lang_stats.get(lang, 0) + 1
                    total_size += stat.st_size

            elapsed = (time.monotonic() - start) * 1000
            logger.info(
                "Scanned %s: %d files, %d languages, %.0fms",
                project_path.name, len(files), len(lang_stats), elapsed,
            )

            return ProjectScanResult(
                project_path=str(project_path),
                file_tree=files,
                language_stats=dict(sorted(lang_stats.items(), key=lambda x: -x[1])),
                total_files=len(files),
                total_size_bytes=total_size,
                scan_duration_ms=round(elapsed, 2),
            )

        except PermissionError as e:
            logger.warning("Permission denied scanning %s: %s", project_path, e)
            return ProjectScanResult(
                project_path=str(project_path),
                error=f"Permission denied: {e}",
                scan_duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            logger.error("Scan error for %s: %s", project_path, e)
            return ProjectScanResult(
                project_path=str(project_path),
                error=str(e),
                scan_duration_ms=(time.monotonic() - start) * 1000,
            )

    def get_recent_changes(
        self, project_path: str | Path, since_seconds: float = 3600,
    ) -> list[FileEntry]:
        """Get files modified within a recent time window.

        Args:
            project_path: Root path of the project.
            since_seconds: Time window in seconds (default: 1 hour).

        Returns:
            List of FileEntry objects modified within the window.
        """
        result = self.scan_project(project_path)
        if result.error:
            return []

        now = time.time()
        cutoff = now - since_seconds
        return [f for f in result.file_tree if f.last_modified >= cutoff]

    # ── .gitignore Parsing ───────────────────────────────────────────────

    def _load_gitignore(self, project_path: Path) -> list[str]:
        """Load ignore patterns from .gitignore file.

        Args:
            project_path: Root directory containing .gitignore.

        Returns:
            List of glob-style ignore patterns.
        """
        gitignore_path = project_path / ".gitignore"
        patterns: list[str] = list(_DEFAULT_EXCLUDE)

        if gitignore_path.is_file():
            try:
                with open(gitignore_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith("#"):
                            continue
                        # Handle negation (we don't support it yet, just skip)
                        if line.startswith("!"):
                            continue
                        patterns.append(line)
                logger.debug("Loaded %d patterns from %s", len(patterns), gitignore_path)
            except OSError as e:
                logger.debug("Could not read .gitignore: %s", e)

        return patterns

    def _should_ignore(self, path: Path, base: Path) -> bool:
        """Check if a path should be ignored based on patterns.

        Args:
            path: Full path to check.
            base: Project root path for relative matching.

        Returns:
            True if the path should be ignored.
        """
        try:
            rel = str(path.relative_to(base)).replace("\\", "/")
        except ValueError:
            return False

        name = path.name

        for pattern in self._ignore_patterns:
            # Match against name (for simple patterns)
            if fnmatch.fnmatch(name, pattern):
                return True
            # Match against relative path (for directory patterns)
            if "/" in pattern and fnmatch.fnmatch(rel, pattern):
                return True
            # Match against path with trailing /**
            if pattern.endswith("/**") and fnmatch.fnmatch(rel, pattern):
                return True

        return False