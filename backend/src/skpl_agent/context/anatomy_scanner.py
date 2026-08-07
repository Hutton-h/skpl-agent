"""
Anatomy Scanner — Asynchronous project scanning for symbol extraction.

Supports full scans, incremental scans (via file watcher), file filtering
(globs, ignores, size limits), and parallel symbol extraction across
multiple worker processes.

Architecture:
    ScanRequest → ScanTaskManager → ThreadPoolExecutor workers
    Each worker: read file → detect language → extract symbols → store
    Frontend receives progress via WebSocket events.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from skpl_agent.context.anatomy_store import (
    AnatomyStore,
    AnatomyStoreMode,
    AnatomyStoreProtocol,
)
from skpl_agent.context.sensitive_filter import SensitiveContentFilter
from skpl_agent.context.symbol_extractor import (
    DescriptionExtractor,
    Symbol,
    SymbolExtractor,
    detect_language,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Directories always ignored during scanning
DEFAULT_IGNORE_DIRS: set[str] = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "virtualenv",
    ".tox",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    ".vs",
    "bower_components",
    ".next",
    ".nuxt",
    "vendor",
    ".terraform",
    ".skpl",
    "coverage",
    ".nyc_output",
}

# Files always ignored
DEFAULT_IGNORE_FILES: set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "Gemfile.lock",
    "poetry.lock",
    "Pipfile.lock",
    "go.sum",
    "composer.lock",
}

# Extensions to scan
DEFAULT_SCAN_EXTENSIONS: set[str] = {
    ".py", ".pyi", ".pyx",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go",
    ".rs",
    ".java", ".kt", ".kts", ".scala",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".lua",
    ".sh", ".bash", ".zsh",
    ".sql",
    ".html", ".htm",
    ".css", ".scss", ".less",
    ".json", ".yaml", ".yml",
    ".md", ".mdx",
    ".toml",
    ".xml",
    ".vue", ".svelte",
    ".r",
    ".dart",
    ".elm",
    ".ex", ".exs", ".erl", ".hrl",
    ".hs",
    ".clj", ".cljs",
    ".ml", ".mli",
    ".zig",
    ".nim",
}

# Maximum file size to scan (1 MB)
MAX_FILE_SIZE_BYTES: int = 1 * 1024 * 1024

# Default max workers for parallel scanning
DEFAULT_MAX_WORKERS: int = 4


# ---------------------------------------------------------------------------
# Scan Modes & Results
# ---------------------------------------------------------------------------


class ScanMode(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class ScanOptions:
    """Configuration for a scan operation."""

    mode: ScanMode = ScanMode.FULL
    root_path: Path = field(default_factory=Path.cwd)
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    ignore_dirs: set[str] = field(default_factory=lambda: DEFAULT_IGNORE_DIRS.copy())
    ignore_files: set[str] = field(default_factory=lambda: DEFAULT_IGNORE_FILES.copy())
    scan_extensions: set[str] = field(default_factory=lambda: DEFAULT_SCAN_EXTENSIONS.copy())
    max_file_size: int = MAX_FILE_SIZE_BYTES
    max_workers: int = DEFAULT_MAX_WORKERS
    store_mode: AnatomyStoreMode = AnatomyStoreMode.SQLITE
    store_path: str = ".skpl/anatomy.db"
    # For incremental scans: only scan files modified after this timestamp
    changed_files: list[str] = field(default_factory=list)
    # Progress callback: (current, total, file_path)
    on_progress: Optional[Callable[[int, int, str], None]] = None
    # Sensitive content filter
    filter_sensitive: bool = True


@dataclass
class ScanResult:
    """Result of a scan operation."""

    mode: ScanMode
    total_files_scanned: int = 0
    total_symbols_extracted: int = 0
    total_files_skipped: int = 0
    total_files_filtered: int = 0  # sensitive files filtered
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    languages_found: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# File Scanner
# ---------------------------------------------------------------------------


class AnatomyScanner:
    """Scans project directories and extracts symbols from source files.

    Usage:
        scanner = AnatomyScanner(ScanOptions(root_path="/path/to/project"))
        result = await scanner.scan()
    """

    def __init__(self, options: ScanOptions | None = None):
        self.options = options or ScanOptions()
        self._store: AnatomyStoreProtocol | None = None
        self._filter = SensitiveContentFilter() if self.options.filter_sensitive else None

    @property
    def store(self) -> AnatomyStoreProtocol:
        if self._store is None:
            store_path = Path(self.options.root_path) / self.options.store_path
            self._store = AnatomyStore.create(self.options.store_mode, store_path)
        return self._store

    def _should_ignore_dir(self, dir_name: str, dir_path: Path) -> bool:
        """Check if a directory should be ignored."""
        if dir_name in self.options.ignore_dirs:
            return True
        if dir_name.startswith(".") and dir_name not in (".github", ".circleci"):
            return True
        # Check exclude patterns
        rel_path = str(dir_path.relative_to(self.options.root_path))
        for pattern in self.options.exclude_patterns:
            if Path(rel_path).match(pattern):
                return True
        return False

    def _should_scan_file(self, file_path: Path) -> bool:
        """Check if a file should be scanned."""
        # Check extension
        if file_path.suffix.lower() not in self.options.scan_extensions:
            return False
        # Check file name
        if file_path.name in self.options.ignore_files:
            return False
        # Check size
        try:
            if file_path.stat().st_size > self.options.max_file_size:
                return False
        except OSError:
            return False
        # Check sensitive content
        if self._filter:
            if self._filter.is_sensitive_filename(file_path.name):
                return False
        return True

    def _collect_files(self) -> list[Path]:
        """Collect all files to scan."""
        if self.options.mode == ScanMode.INCREMENTAL and self.options.changed_files:
            return [
                Path(self.options.root_path) / f
                for f in self.options.changed_files
                if (Path(self.options.root_path) / f).exists()
            ]

        files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.options.root_path):
            # Filter directories in-place
            dirnames[:] = [
                d
                for d in dirnames
                if not self._should_ignore_dir(d, Path(dirpath) / d)
            ]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                if self._should_scan_file(file_path):
                    files.append(file_path)

        return files

    def _scan_single_file(self, file_path: Path) -> tuple[Path, list[Symbol], Optional[str]]:
        """Scan a single file and return extracted symbols."""
        error = None
        symbols: list[Symbol] = []

        try:
            # Check sensitive content
            if self._filter:
                source = file_path.read_text(encoding="utf-8", errors="replace")
                if self._filter.contains_sensitive_content(source):
                    return file_path, [], "sensitive_content_filtered"

            language = detect_language(file_path)
            if language == "unknown":
                return file_path, [], None

            symbols = SymbolExtractor.from_file(file_path)

            # Extract descriptions
            if symbols:
                source = file_path.read_text(encoding="utf-8", errors="replace")
                for sym in symbols:
                    sym.description = DescriptionExtractor.extract_symbol_description(
                        source, sym, language
                    )

        except Exception as e:
            error = f"{file_path}: {e}"

        return file_path, symbols, error

    async def scan(self) -> ScanResult:
        """Run the scan asynchronously."""
        start_time = time.monotonic()
        result = ScanResult(mode=self.options.mode)

        # Collect files
        files = self._collect_files()
        result.total_files_scanned = len(files)

        if not files:
            result.duration_seconds = time.monotonic() - start_time
            return result

        # Parallel scan using ThreadPoolExecutor
        loop = asyncio.get_running_loop()
        lang_counts: dict[str, int] = {}
        processed = 0

        with ThreadPoolExecutor(max_workers=self.options.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self._scan_single_file, f): f for f in files
            }

            for future in as_completed(futures):
                file_path, symbols, error = await loop.run_in_executor(
                    None, future.result
                )

                processed += 1

                if error == "sensitive_content_filtered":
                    result.total_files_filtered += 1
                elif error:
                    result.errors.append(error)
                    result.total_files_skipped += 1
                elif symbols:
                    # Store symbols
                    for sym in symbols:
                        self.store.upsert_symbol(str(file_path), sym)
                        lang_counts[sym.language] = (
                            lang_counts.get(sym.language, 0) + 1
                        )
                    result.total_symbols_extracted += len(symbols)

                # Progress callback
                if self.options.on_progress:
                    self.options.on_progress(processed, len(files), str(file_path))

        result.languages_found = lang_counts
        result.duration_seconds = time.monotonic() - start_time
        return result

    def scan_sync(self) -> ScanResult:
        """Run the scan synchronously (for non-async contexts)."""
        return asyncio.run(self.scan())

    def close(self) -> None:
        """Close the underlying store."""
        if self._store:
            self._store.close()
            self._store = None


# ---------------------------------------------------------------------------
# File Hash Computation
# ---------------------------------------------------------------------------


def compute_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str | None:
    """Compute a hash of a file for change detection."""
    try:
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, ValueError):
        return None


def compute_source_hash(source: str, algorithm: str = "sha256") -> str:
    """Compute a hash of source code text."""
    return hashlib.new(algorithm, source.encode("utf-8", errors="replace")).hexdigest()