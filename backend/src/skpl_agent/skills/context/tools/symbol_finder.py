"""Symbol finder — locate code symbols and their references.

Uses regex-based pattern matching to find symbol definitions and
references across a project. Designed as a lightweight alternative
that does not require tree-sitter or language server dependencies.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Regex patterns for symbol definitions in various languages
_LANG_DEF_PATTERNS: dict[str, str] = {
    ".py": r"^\s*(?:def|class|async def)\s+{symbol}\b",
    ".ts": r"(?:export\s+)?(?:const|let|var|function|class|interface|type|enum)\s+{symbol}\b",
    ".tsx": r"(?:export\s+)?(?:const|let|var|function|class|interface|type|enum)\s+{symbol}\b",
    ".js": r"(?:const|let|var|function|class)\s+{symbol}\b",
    ".jsx": r"(?:const|let|var|function|class)\s+{symbol}\b",
    ".go": r"(?:func|type|var|const)\s+{symbol}\b",
    ".rs": r"(?:fn|struct|enum|trait|impl|type|const|static|let\s+mut\s+{symbol}|let\s+{symbol})\b",
    ".java": r"(?:class|interface|enum|record)\s+{symbol}\b",
    ".c": r"(?:void|int|char|float|double|long|short|struct|enum|typedef)\s+\*?\s*{symbol}\b",
    ".cpp": r"(?:class|struct|enum|void|int|auto|template)\s+{symbol}\b",
    ".h": r"(?:void|int|char|float|double|struct|enum|class)\s+\*?\s*{symbol}\b",
    ".hpp": r"(?:class|struct|enum|void|int|auto|template)\s+{symbol}\b",
    ".cs": r"(?:class|struct|interface|enum|record|void|int|string|var)\s+{symbol}\b",
    ".rb": r"(?:def|class|module)\s+{symbol}\b",
    ".php": r"(?:function|class|interface|trait)\s+{symbol}\b",
    ".kt": r"(?:fun|class|interface|object|val|var)\s+{symbol}\b",
    ".swift": r"(?:func|class|struct|enum|protocol|let|var)\s+{symbol}\b",
}

# Patterns for finding references (any occurrence of the symbol name)
_REF_PATTERN = r"\b{symbol}\b"

# Comment patterns to skip (language-specific)
_COMMENT_PATTERNS: dict[str, list[str]] = {
    ".py": [r"#.*$", r'""".*?"""', r"'''.*?'''"],
    ".ts": [r"//.*$", r"/\*.*?\*/"],
    ".tsx": [r"//.*$", r"/\*.*?\*/"],
    ".js": [r"//.*$", r"/\*.*?\*/"],
    ".jsx": [r"//.*$", r"/\*.*?\*/"],
    ".go": [r"//.*$"],
    ".rs": [r"//.*$", r"/\*.*?\*/"],
    ".java": [r"//.*$", r"/\*.*?\*/"],
    ".c": [r"//.*$", r"/\*.*?\*/"],
    ".cpp": [r"//.*$", r"/\*.*?\*/"],
    ".h": [r"//.*$", r"/\*.*?\*/"],
    ".hpp": [r"//.*$", r"/\*.*?\*/"],
    ".cs": [r"//.*$", r"/\*.*?\*/"],
    ".rb": [r"#.*$"],
    ".php": [r"//.*$", r"#.*$", r"/\*.*?\*/"],
    ".kt": [r"//.*$", r"/\*.*?\*/"],
    ".swift": [r"//.*$", r"/\*.*?\*/"],
}


@dataclass
class SymbolResult:
    """Result of a symbol lookup.

    Attributes:
        symbol_name: The queried symbol name.
        definitions: List of (file_path, line_number, line_content) tuples
                     where the symbol is defined.
        references: List of (file_path, line_number, line_content) tuples
                    where the symbol is referenced.
        total_definitions: Count of definitions found.
        total_references: Count of references found.
        duration_ms: Time taken for the search.
        error: Error message if the search failed.
    """

    symbol_name: str
    definitions: list[tuple[str, int, str]] = field(default_factory=list)
    references: list[tuple[str, int, str]] = field(default_factory=list)
    total_definitions: int = 0
    total_references: int = 0
    duration_ms: float = 0.0
    error: str = ""


class SymbolFinder:
    """Finds code symbols and their references using regex patterns.

    Provides language-aware symbol definition and reference lookup
    without requiring external parser dependencies.

    Usage:
        >>> finder = SymbolFinder()
        >>> result = finder.find_symbol("/path/to/project", "MyClass")
        >>> for file, line, content in result.definitions:
        >>>     print(f"  {file}:{line}: {content}")
    """

    # Source file extensions to scan
    _SOURCE_EXTENSIONS = frozenset(_LANG_DEF_PATTERNS.keys())

    # Directories to skip during scan
    _SKIP_DIRS = frozenset({
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".next", ".turbo", ".cache",
    })

    def __init__(self) -> None:
        pass

    # ── Main API ─────────────────────────────────────────────────────────

    def find_symbol(
        self, project_path: str | Path, symbol_name: str,
    ) -> SymbolResult:
        """Find all definitions of a symbol in the project.

        Args:
            project_path: Root path of the project to search.
            symbol_name: Name of the symbol to find.

        Returns:
            SymbolResult with definition locations.
        """
        start = time.monotonic()
        project_path = Path(project_path).resolve()

        if not project_path.is_dir():
            return SymbolResult(
                symbol_name=symbol_name,
                error=f"Not a directory: {project_path}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            definitions, _ = self._search_symbol(
                project_path, symbol_name, find_definitions=True, find_references=False,
            )
            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "Found %d definitions of '%s' in %s (%.0fms)",
                len(definitions), symbol_name, project_path.name, elapsed,
            )

            return SymbolResult(
                symbol_name=symbol_name,
                definitions=definitions,
                total_definitions=len(definitions),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error("Symbol search error for '%s': %s", symbol_name, e)
            return SymbolResult(
                symbol_name=symbol_name,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    def find_references(
        self, project_path: str | Path, symbol_name: str,
    ) -> SymbolResult:
        """Find all references to a symbol across the project.

        Args:
            project_path: Root path of the project to search.
            symbol_name: Name of the symbol to find references for.

        Returns:
            SymbolResult with reference locations.
        """
        start = time.monotonic()
        project_path = Path(project_path).resolve()

        if not project_path.is_dir():
            return SymbolResult(
                symbol_name=symbol_name,
                error=f"Not a directory: {project_path}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            definitions, references = self._search_symbol(
                project_path, symbol_name, find_definitions=True, find_references=True,
            )
            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "Found %d defs, %d refs of '%s' in %s (%.0fms)",
                len(definitions), len(references), symbol_name, project_path.name, elapsed,
            )

            return SymbolResult(
                symbol_name=symbol_name,
                definitions=definitions,
                references=references,
                total_definitions=len(definitions),
                total_references=len(references),
                duration_ms=round(elapsed, 2),
            )

        except Exception as e:
            logger.error("Reference search error for '%s': %s", symbol_name, e)
            return SymbolResult(
                symbol_name=symbol_name,
                error=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    # ── Internal Search ──────────────────────────────────────────────────

    def _search_symbol(
        self,
        project_path: Path,
        symbol_name: str,
        find_definitions: bool = True,
        find_references: bool = False,
    ) -> tuple[list[tuple[str, int, str]], list[tuple[str, int, str]]]:
        """Internal search method for both definitions and references.

        Args:
            project_path: Root path to search.
            symbol_name: Symbol name to search for.
            find_definitions: Whether to collect definition matches.
            find_references: Whether to collect reference matches.

        Returns:
            Tuple of (definitions, references) as lists of
            (file_path, line_number, line_content) tuples.
        """
        definitions: list[tuple[str, int, str]] = []
        references: list[tuple[str, int, str]] = []

        for file_path in project_path.rglob("*"):
            if file_path.is_dir():
                continue
            if file_path.name.startswith("."):
                continue
            if any(p in file_path.parts for p in self._SKIP_DIRS):
                continue

            ext = file_path.suffix.lower()
            if ext not in self._SOURCE_EXTENSIONS:
                continue

            try:
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue

            # Build comment removal patterns
            comment_patterns = _COMMENT_PATTERNS.get(ext, [])

            # Build definition regex
            if find_definitions and ext in _LANG_DEF_PATTERNS:
                def_pattern = _LANG_DEF_PATTERNS[ext].format(
                    symbol=re.escape(symbol_name),
                )
                def_re = re.compile(def_pattern, re.MULTILINE)

            # Build reference regex
            if find_references:
                ref_pattern = _REF_PATTERN.format(symbol=re.escape(symbol_name))
                ref_re = re.compile(ref_pattern)

            for line_num, line in enumerate(lines, start=1):
                # Strip comments for definition matching
                clean_line = line
                for cp in comment_patterns:
                    clean_line = re.sub(cp, "", clean_line, flags=re.DOTALL)

                # Check definition
                if find_definitions and ext in _LANG_DEF_PATTERNS:
                    if def_re.search(clean_line):
                        definitions.append(
                            (str(file_path), line_num, line.rstrip("\n\r")),
                        )

                # Check reference
                if find_references:
                    # Only count as reference if not already a definition
                    is_def = any(
                        d[0] == str(file_path) and d[1] == line_num
                        for d in definitions
                    )
                    if not is_def and ref_re.search(line):
                        references.append(
                            (str(file_path), line_num, line.rstrip("\n\r")),
                        )

        return definitions, references