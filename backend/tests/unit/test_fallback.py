"""Tests for context fallback strategy."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from skpl_agent.context.fallback import (
    CommentsExtractor,
    ContextFallbackStrategy,
    FallbackContext,
    FileHeuristicScanner,
)


class TestFileHeuristicScanner:
    """Tests for FileHeuristicScanner."""

    def test_scan_empty_directory(self) -> None:
        """Scanning an empty directory returns empty context."""
        scanner = FileHeuristicScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = scanner.scan(Path(tmpdir))
            assert ctx.source == "heuristic"
            assert ctx.file_list == []

    def test_scan_with_files(self) -> None:
        """Scanning a directory with files returns file list."""
        scanner = FileHeuristicScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "main.py").write_text("print('hello')")
            (root / "utils.py").write_text("def foo(): pass")
            (root / "README.md").write_text("# Project")

            ctx = scanner.scan(root)
            assert ctx.source == "heuristic"
            assert len(ctx.file_list) == 3
            assert ctx.symbol_count == 0

    def test_scan_nonexistent_directory(self) -> None:
        """Scanning a nonexistent directory returns none context."""
        scanner = FileHeuristicScanner()
        ctx = scanner.scan(Path("/nonexistent/path"))
        assert ctx.source == "none"

    def test_scan_ignores_git(self) -> None:
        """Scanning ignores .git directory."""
        scanner = FileHeuristicScanner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "main.py").write_text("print('hello')")
            git_dir = root / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("config")

            ctx = scanner.scan(root)
            filenames = [Path(f).name for f in ctx.file_list]
            assert "main.py" in filenames
            assert "config" not in filenames

    def test_scan_max_files_limit(self) -> None:
        """Scanning respects max_files limit."""
        scanner = FileHeuristicScanner(max_files=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for i in range(10):
                (root / f"file_{i}.py").write_text(f"# file {i}")

            ctx = scanner.scan(root, max_files=2)
            assert len(ctx.file_list) == 2

    def test_format_size(self) -> None:
        """_format_size formats bytes correctly."""
        assert FileHeuristicScanner._format_size(0) == "0.0 B"
        assert FileHeuristicScanner._format_size(500) == "500.0 B"
        assert FileHeuristicScanner._format_size(1024) == "1.0 KB"
        assert FileHeuristicScanner._format_size(1536) == "1.5 KB"
        assert FileHeuristicScanner._format_size(1048576) == "1.0 MB"


class TestCommentsExtractor:
    """Tests for CommentsExtractor."""

    def test_extract_python_comments(self) -> None:
        """Extracts leading comments from Python files."""
        extractor = CommentsExtractor()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "module.py").write_text(
                '"""Module docstring."""\n\n'
                "# A helper function\n"
                "def foo():\n"
                '    """Function docstring."""\n'
                "    pass\n"
            )

            ctx = extractor.extract(root)
            assert ctx.source == "comments"
            assert ctx.symbol_count >= 1

    def test_extract_js_comments(self) -> None:
        """Extracts leading comments from JavaScript files."""
        extractor = CommentsExtractor()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "app.js").write_text(
                "// Application entry point\n"
                "// Version 1.0.0\n"
                "const app = {};\n"
            )

            ctx = extractor.extract(root)
            assert ctx.source == "comments"
            assert ctx.symbol_count >= 1

    def test_extract_empty_directory(self) -> None:
        """Extracting from empty directory returns empty context."""
        extractor = CommentsExtractor()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = extractor.extract(Path(tmpdir))
            assert ctx.source == "comments"
            assert ctx.symbol_count == 0

    def test_extract_ignores_non_source_files(self) -> None:
        """Extracting ignores files without comment patterns."""
        extractor = CommentsExtractor()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data.bin").write_bytes(b"\x00\x01\x02")
            (root / "image.png").write_bytes(b"\x89PNG")

            ctx = extractor.extract(root)
            assert ctx.symbol_count == 0

    def test_extract_max_files(self) -> None:
        """Extracting respects max_files limit."""
        extractor = CommentsExtractor(max_files=2)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for i in range(5):
                (root / f"file_{i}.py").write_text(f"# File {i}\ndef func_{i}(): pass\n")

            ctx = extractor.extract(root, max_files=2)
            assert ctx.symbol_count <= 2


class TestContextFallbackStrategy:
    """Tests for ContextFallbackStrategy."""

    @pytest.mark.asyncio
    async def test_heuristic_fallback(self) -> None:
        """Strategy falls back to heuristic when cache is empty."""
        strategy = ContextFallbackStrategy(
            enable_cache=False,
            enable_heuristic=True,
            enable_comments=False,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "main.py").write_text("print('hello')")

            result = await strategy.assemble(root, "session-1")
            assert result.success is True
            assert result.tier == 2
            assert result.context is not None

    @pytest.mark.asyncio
    async def test_comments_fallback_when_heuristic_empty(self) -> None:
        """Strategy falls back to comments when heuristic returns empty."""
        strategy = ContextFallbackStrategy(
            enable_cache=False,
            enable_heuristic=True,
            enable_comments=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await strategy.assemble(Path(tmpdir), "session-1")
            # Empty directory should fall through to comments, then to tier 4
            assert result.context is not None

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Strategy returns cached context on second call."""
        strategy = ContextFallbackStrategy(
            enable_cache=True,
            enable_heuristic=True,
            enable_comments=False,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "main.py").write_text("print('hello')")

            result1 = await strategy.assemble(root, "session-1")
            assert result1.tier == 2  # Heuristic

            result2 = await strategy.assemble(root, "session-2")
            assert result2.tier == 1  # Cached

    @pytest.mark.asyncio
    async def test_all_fallbacks_disabled(self) -> None:
        """Strategy returns tier 4 when all fallbacks are disabled."""
        strategy = ContextFallbackStrategy(
            enable_cache=False,
            enable_heuristic=False,
            enable_comments=False,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "main.py").write_text("print('hello')")

            result = await strategy.assemble(root, "session-1")
            assert result.success is False
            assert result.tier == 4

    def test_clear_cache(self) -> None:
        """clear_cache removes all cached entries."""
        strategy = ContextFallbackStrategy()
        strategy._cache["/test"] = FallbackContext(source="cached", summary="test")
        strategy.clear_cache()
        assert len(strategy._cache) == 0

    def test_invalidate_cache(self) -> None:
        """invalidate_cache removes a specific entry."""
        strategy = ContextFallbackStrategy()
        strategy._cache["/test"] = FallbackContext(source="cached", summary="test")
        strategy._cache["/other"] = FallbackContext(source="cached", summary="other")
        strategy.invalidate_cache(Path("/test"))
        assert "/test" not in strategy._cache
        assert "/other" in strategy._cache