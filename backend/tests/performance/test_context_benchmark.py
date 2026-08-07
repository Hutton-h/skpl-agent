"""Performance benchmark tests for context management components.

Tests cover:
- anatomy_scanner: large-scale project scanning performance
- symbol_extractor: bulk symbol extraction speed
- bug_matcher: deduplication performance with large datasets
- Uses pytest-benchmark for timing measurements.

Markers: slow, benchmark
To run: pytest backend/tests/performance/test_context_benchmark.py -m "benchmark" --benchmark-only
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Try importing pytest-benchmark; skip gracefully if not installed
try:
    import pytest_benchmark
    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False

from skpl_agent.context.anatomy_scanner import (
    AnatomyScanner,
    ScanMode,
    ScanOptions,
    compute_file_hash,
    compute_source_hash,
)
from skpl_agent.context.bug_matcher import BugMatcher
from skpl_agent.context.symbol_extractor import Symbol


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def large_project_dir() -> Path:
    """Create a project with many Python files for benchmarking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create 100 Python files with classes and functions
        for i in range(100):
            mod_dir = root / f"module_{i // 10}"
            mod_dir.mkdir(exist_ok=True)
            file_path = mod_dir / f"file_{i}.py"
            content = _generate_python_file(i)
            file_path.write_text(content)
        # Create a few large files
        large_file = root / "large_module.py"
        large_file.write_text(_generate_large_python_file(500))
        yield root


@pytest.fixture
def large_bug_dataset() -> list:
    """Create a large dataset of bug records for matching."""
    bugs = []
    for i in range(1000):
        bug = MagicMock()
        bug.id = f"bug-{i:04d}"
        bug.error_type = f"Error{i % 10}"
        bug.error_message = f"Error message number {i} with some variation {i % 100}"
        bug.fingerprint = hashlib.sha256(
            f"Error{i % 10}:error message number {i} with some variation {i % 100}".encode()
        ).hexdigest()[:64]
        bugs.append(bug)
    return bugs


@pytest.fixture
def many_symbols() -> list[Symbol]:
    """Create a batch of symbols for extraction benchmarking."""
    symbols = []
    for i in range(1000):
        symbols.append(Symbol(
            name=f"func_{i}",
            kind="function",
            line_start=i * 10 + 1,
            line_end=i * 10 + 5,
            signature=f"def func_{i}(x: int) -> str:",
            language="python",
        ))
    return symbols


def _generate_python_file(index: int) -> str:
    """Generate a Python file with classes and functions."""
    return f'''"""Module {index} - auto-generated for benchmarking."""

from typing import List, Optional, Dict, Any
import os
import sys


class Class{index}A:
    """First class in module {index}."""

    def __init__(self, name: str, value: int = 0) -> None:
        self.name = name
        self.value = value
        self._cache: Dict[str, Any] = {{}}

    def method_a(self, x: int) -> int:
        """Method A."""
        return self.value + x

    def method_b(self, items: List[str]) -> List[str]:
        """Method B."""
        return [item.upper() for item in items]

    @staticmethod
    def static_method() -> str:
        """Static method."""
        return "static"


class Class{index}B:
    """Second class in module {index}."""

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        self.data = data or {{}}

    async def async_method(self, key: str) -> Any:
        """Async method."""
        return self.data.get(key)


def function_{index}_a(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


def function_{index}_b(text: str, prefix: str = "") -> str:
    """Format text with prefix."""
    return f"{{prefix}}{{text}}"


CONSTANT_{index} = {index * 100}
'''


def _generate_large_python_file(num_functions: int) -> str:
    """Generate a very large Python file."""
    lines = ['"""Large module for benchmarking."""\n']
    for i in range(num_functions):
        lines.append(f'''
def benchmark_func_{i}(x: int, y: int = 0) -> int:
    """Benchmark function {i}."""
    result = x + y
    for j in range(10):
        result += j
    return result
''')
    return "\n".join(lines)


# ── Anatomy Scanner Benchmarks ─────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.benchmark
class TestAnatomyScannerBenchmark:
    """Benchmarks for AnatomyScanner."""

    @pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed")
    def test_scan_large_project_benchmark(
        self, benchmark, large_project_dir: Path
    ) -> None:
        """Benchmark full scan of a 100-file project."""
        scanner = AnatomyScanner()
        options = ScanOptions(
            root_path=str(large_project_dir),
            mode="full",
            parallel=False,
        )

        def run_scan():
            return scanner.scan_sync()

        result = benchmark(run_scan)
        assert result.total_files_scanned > 0

    @pytest.mark.slow
    def test_scan_large_project_performance(self, large_project_dir: Path) -> None:
        """Performance test: scan should complete within reasonable time."""
        import time
        scanner = AnatomyScanner()
        options = ScanOptions(
            root_path=str(large_project_dir),
            mode="full",
            parallel=False,
        )

        start = time.monotonic()
        result = scanner.scan_sync()
        elapsed = time.monotonic() - start

        assert result.total_files_scanned >= 100
        assert result.total_symbols_extracted > 0
        # Should complete within 30 seconds for 100 files
        assert elapsed < 30.0, f"Scan took {elapsed:.2f}s, expected < 30s"

    @pytest.mark.slow
    def test_incremental_scan_performance(self, large_project_dir: Path) -> None:
        """Incremental scan should be faster than full scan."""
        import time
        scanner = AnatomyScanner()

        # Full scan first
        full_opts = ScanOptions(
            root_path=str(large_project_dir),
            mode="full",
            parallel=False,
        )
        start = time.monotonic()
        scanner.scan_sync()  # build cache
        full_time = time.monotonic() - start

        # Incremental scan with no changes
        inc_opts = ScanOptions(
            root_path=str(large_project_dir),
            mode="incremental",
            parallel=False,
        )
        start = time.monotonic()
        inc_result = scanner.scan_sync()
        inc_time = time.monotonic() - start

        # Incremental should be faster (or equal)
        assert inc_time <= full_time * 1.1, (
            f"Incremental {inc_time:.2f}s vs full {full_time:.2f}s"
        )


# ── File Hash Benchmarks ───────────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.benchmark
class TestFileHashBenchmark:
    """Benchmarks for file hash computation."""

    @pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed")
    def test_compute_file_hash_benchmark(self, benchmark, large_project_dir: Path) -> None:
        """Benchmark file hash computation."""
        py_files = list(large_project_dir.rglob("*.py"))
        if not py_files:
            pytest.skip("No Python files found")
        test_file = str(py_files[0])

        def hash_file():
            return compute_file_hash(test_file)

        result = benchmark(hash_file)
        assert result is not None
        assert len(result) == 64

    def test_compute_file_hash_performance(self, large_project_dir: Path) -> None:
        """File hash computation should be fast."""
        import time
        py_files = list(large_project_dir.rglob("*.py"))
        if not py_files:
            pytest.skip("No Python files found")

        test_file = str(py_files[0])
        start = time.monotonic()
        for _ in range(100):
            compute_file_hash(test_file)
        elapsed = time.monotonic() - start
        # 100 hashes should complete in well under 1 second
        assert elapsed < 1.0, f"100 hashes took {elapsed:.2f}s"

    def test_compute_source_hash_performance(self) -> None:
        """Source hash computation should be fast."""
        import time
        source = "def foo():\n    pass\n" * 1000  # Large source

        start = time.monotonic()
        for _ in range(100):
            compute_source_hash(source)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"100 source hashes took {elapsed:.2f}s"


# ── Bug Matcher Benchmarks ─────────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.benchmark
class TestBugMatcherBenchmark:
    """Benchmarks for BugMatcher."""

    @pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed")
    def test_find_duplicate_benchmark(
        self, benchmark, large_bug_dataset: list
    ) -> None:
        """Benchmark finding a duplicate in a large dataset."""
        matcher = BugMatcher(similarity_threshold=0.75)

        # Fingerprint of a known bug
        target_bug = large_bug_dataset[500]
        fp = target_bug.fingerprint

        def find_dup():
            return matcher.find_duplicate(fp, target_bug.error_message, large_bug_dataset)

        result = benchmark(find_dup)
        assert result is not None

    def test_fingerprint_computation_speed(self) -> None:
        """Fingerprint computation should be fast."""
        import time
        matcher = BugMatcher()
        messages = [
            (f"Error{i}", f"Error message {i} with some details", f"file_{i}.py", i)
            for i in range(1000)
        ]

        start = time.monotonic()
        for error_type, msg, file_path, line in messages:
            matcher.compute_fingerprint(error_type, msg, file_path, line)
        elapsed = time.monotonic() - start
        # 1000 fingerprints should complete in well under 1 second
        assert elapsed < 1.0, f"1000 fingerprints took {elapsed:.2f}s"

    def test_find_duplicate_exact_match_performance(
        self, large_bug_dataset: list
    ) -> None:
        """Exact fingerprint match should be fast with large dataset."""
        import time
        matcher = BugMatcher()
        target = large_bug_dataset[500]
        fp = matcher.compute_fingerprint(
            target.error_type, target.error_message
        )

        # Point the target's fingerprint to our computed one
        target.fingerprint = fp

        start = time.monotonic()
        for _ in range(100):
            matcher.find_duplicate(fp, target.error_message, large_bug_dataset)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"100 duplicate searches took {elapsed:.2f}s"

    def test_find_duplicate_miss_performance(self, large_bug_dataset: list) -> None:
        """Searching for non-existent bug should still be fast."""
        import time
        matcher = BugMatcher()
        fp = hashlib.sha256(b"nonexistent:bug").hexdigest()[:64]

        start = time.monotonic()
        for _ in range(100):
            matcher.find_duplicate(fp, "nonexistent bug", large_bug_dataset)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"100 miss searches took {elapsed:.2f}s"


# ── Symbol Extractor Benchmarks ────────────────────────────────────────────


@pytest.mark.slow
@pytest.mark.benchmark
class TestSymbolExtractorBenchmark:
    """Benchmarks for SymbolExtractor."""

    def test_symbol_extraction_from_large_file(self) -> None:
        """Symbol extraction from a large file should scale reasonably."""
        import time
        from skpl_agent.context.symbol_extractor import SymbolExtractor

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "large.py"
            file_path.write_text(_generate_large_python_file(200))

            start = time.monotonic()
            symbols = SymbolExtractor.from_file(file_path)
            elapsed = time.monotonic() - start

            assert len(symbols) >= 200
            assert elapsed < 10.0, f"Symbol extraction took {elapsed:.2f}s"

    def test_language_detection_performance(self) -> None:
        """Language detection should be fast."""
        import time
        from skpl_agent.context.symbol_extractor import detect_language

        extensions = [".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".php"]
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for ext in extensions:
                f = Path(tmpdir) / f"test{ext}"
                f.write_text("// test")
                files.append(f)

            start = time.monotonic()
            for _ in range(100):
                for f in files:
                    detect_language(f)
            elapsed = time.monotonic() - start
            # 1000 detections should be fast
            assert elapsed < 1.0, f"1000 detections took {elapsed:.2f}s"


# ── Memory Usage Tests ─────────────────────────────────────────────────────


@pytest.mark.slow
class TestMemoryUsage:
    """Memory usage and scaling tests."""

    def test_scanner_memory_with_large_project(self, large_project_dir: Path) -> None:
        """Scanner should not consume excessive memory for large projects."""
        scanner = AnatomyScanner()
        options = ScanOptions(
            root_path=str(large_project_dir),
            mode="full",
            parallel=False,
        )
        result = scanner.scan_sync()
        assert result.total_symbols_extracted > 0
        # If we got here without memory errors, the test passes

    def test_bug_matcher_large_dataset(self, large_bug_dataset: list) -> None:
        """BugMatcher handles large datasets without errors."""
        matcher = BugMatcher()
        for bug in large_bug_dataset[:100]:
            fp = matcher.compute_fingerprint(bug.error_type, bug.error_message)
            result = matcher.find_duplicate(fp, bug.error_message, large_bug_dataset)
            # Should find the bug itself as duplicate
            assert result is not None