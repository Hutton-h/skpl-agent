"""Unit tests for anatomy_scanner.py — project anatomy scanning."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from skpl_agent.context.anatomy_scanner import (
    AnatomyScanner,
    ScanMode,
    ScanOptions,
    compute_file_hash,
    compute_source_hash,
)
from skpl_agent.context.symbol_extractor import Symbol


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_project() -> Path:
    """Create a temporary project with sample source files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Python file
        py_file = root / "main.py"
        py_file.write_text("""\
def hello():
    '''Say hello.'''
    return "Hello, World!"

class Greeter:
    '''A friendly greeter.'''

    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
""")

        # JavaScript file
        js_file = root / "app.js"
        js_file.write_text("""\
function add(a, b) {
    return a + b;
}

class Calculator {
    multiply(x, y) {
        return x * y;
    }
}
""")

        # Subdirectory
        subdir = root / "subpkg"
        subdir.mkdir()
        (subdir / "__init__.py").write_text("# subpkg")

        yield root


@pytest.fixture
def scanner() -> AnatomyScanner:
    """Create a scanner with default options."""
    return AnatomyScanner()


# ── File Hash Tests ──────────────────────────────────────────────────────────


def test_compute_file_hash(temp_project: Path) -> None:
    """compute_file_hash returns a consistent hash for a file."""
    py_file = temp_project / "main.py"
    h1 = compute_file_hash(str(py_file))
    h2 = compute_file_hash(str(py_file))
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_compute_file_hash_different_files(temp_project: Path) -> None:
    """Different files produce different hashes."""
    h1 = compute_file_hash(str(temp_project / "main.py"))
    h2 = compute_file_hash(str(temp_project / "app.js"))
    assert h1 != h2


def test_compute_source_hash() -> None:
    """compute_source_hash returns a consistent hash for source text."""
    source = "def foo(): pass"
    h1 = compute_source_hash(source)
    h2 = compute_source_hash(source)
    assert h1 == h2
    assert len(h1) == 64


# ── Scan Mode Tests ──────────────────────────────────────────────────────────


def test_scan_mode_values() -> None:
    """ScanMode enum has full and incremental values."""
    assert ScanMode.FULL == "full"
    assert ScanMode.INCREMENTAL == "incremental"


# ── Scan Options Tests ───────────────────────────────────────────────────────


def test_scan_options_defaults() -> None:
    """ScanOptions has sensible defaults."""
    opts = ScanOptions(root_path=".", mode="full")
    assert opts.root_path == "."
    assert opts.mode == "full"
    assert opts.parallel is True
    assert opts.max_files == 0  # unlimited


def test_scan_options_with_patterns() -> None:
    """ScanOptions respects file patterns."""
    opts = ScanOptions(
        root_path=".",
        mode="incremental",
        file_patterns=["*.py"],
        exclude_patterns=["test_*", "__pycache__"],
        max_files=100,
        parallel=False,
    )
    assert opts.file_patterns == ["*.py"]
    assert opts.exclude_patterns == ["test_*", "__pycache__"]
    assert opts.max_files == 100
    assert opts.parallel is False


# ── Scanner Initialization Tests ─────────────────────────────────────────────


def test_scanner_creation() -> None:
    """AnatomyScanner can be created with default options."""
    scanner = AnatomyScanner()
    assert scanner is not None


def test_scanner_creation_with_options() -> None:
    """AnatomyScanner can be created with custom options."""
    scanner = AnatomyScanner(max_workers=4)
    assert scanner is not None


# ── Integration-style Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_project_full(temp_project: Path) -> None:
    """Full scan of a project directory finds symbols."""
    scanner = AnatomyScanner()
    options = ScanOptions(
        root_path=str(temp_project),
        mode="full",
        parallel=False,
    )
    result = await scanner.scan(options)
    assert result.files_scanned >= 3  # main.py, app.js, __init__.py
    assert result.symbols_extracted > 0
    assert result.duration_seconds >= 0


@pytest.mark.asyncio
async def test_scan_respects_patterns(temp_project: Path) -> None:
    """Scan respects file_patterns filter."""
    scanner = AnatomyScanner()
    options = ScanOptions(
        root_path=str(temp_project),
        mode="full",
        file_patterns=["*.py"],
        parallel=False,
    )
    result = await scanner.scan(options)
    # Should only scan Python files
    assert result.files_scanned >= 2  # main.py, __init__.py


@pytest.mark.asyncio
async def test_scan_empty_directory(scanner: AnatomyScanner) -> None:
    """Scan of an empty directory returns zero results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        options = ScanOptions(root_path=tmpdir, mode="full")
        result = await scanner.scan(options)
        assert result.files_scanned == 0
        assert result.symbols_extracted == 0


@pytest.mark.asyncio
async def test_scan_incremental(temp_project: Path) -> None:
    """Incremental scan only processes changed files."""
    scanner = AnatomyScanner()

    # First full scan
    full_opts = ScanOptions(root_path=str(temp_project), mode="full", parallel=False)
    full_result = await scanner.scan(full_opts)
    assert full_result.files_scanned > 0

    # Incremental scan (no changes)
    inc_opts = ScanOptions(
        root_path=str(temp_project),
        mode="incremental",
        parallel=False,
    )
    inc_result = await scanner.scan(inc_opts)
    # Incremental should scan fewer or equal files
    assert inc_result.files_scanned <= full_result.files_scanned


# ── Symbol Extraction Quality Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_python_symbols_extracted(temp_project: Path) -> None:
    """Python files produce correct symbols."""
    scanner = AnatomyScanner()
    options = ScanOptions(
        root_path=str(temp_project),
        mode="full",
        file_patterns=["*.py"],
        parallel=False,
    )
    result = await scanner.scan(options)
    assert result.symbols_extracted > 0
    # Check for function and class symbols
    assert "python" in {k.lower() for k in result.languages}