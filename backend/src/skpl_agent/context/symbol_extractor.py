"""
Symbol Extractor for 20+ Programming Languages.

Uses tree-sitter for accurate AST-based symbol extraction, with regex
fallback for languages without tree-sitter grammars. Each language
extractor returns a list of Symbol dataclass instances.

Supported languages:
Python, TypeScript, JavaScript, Go, Rust, Java, C, C++, C#, Ruby,
PHP, Swift, Kotlin, Scala, Lua, Shell, SQL, HTML, CSS, JSON, YAML,
Markdown, and more via regex fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class Symbol:
    """A single symbol extracted from source code."""

    name: str
    kind: str  # function, class, method, variable, type, interface, enum, module, const, etc.
    line_start: int
    line_end: int
    signature: Optional[str] = None
    description: Optional[str] = None
    parent: Optional[str] = None
    is_exported: bool = False
    language: str = ""

    def __hash__(self) -> int:
        return hash((self.name, self.kind, self.line_start, self.parent))


# ---------------------------------------------------------------------------
# Language Mapping
# ---------------------------------------------------------------------------

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".c": "c",
    ".h": "c",
    ".cpp": "c++",
    ".cc": "c++",
    ".cxx": "c++",
    ".hpp": "c++",
    ".hxx": "c++",
    ".cs": "c#",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".less": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".mdx": "markdown",
    ".toml": "toml",
    ".xml": "xml",
    ".vue": "vue",
    ".svelte": "svelte",
    ".r": "r",
    ".dart": "dart",
    ".elm": "elm",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".hs": "haskell",
    ".clj": "clojure",
    ".cljs": "clojure",
    ".ml": "ocaml",
    ".mli": "ocaml",
    ".zig": "zig",
    ".nim": "nim",
}


def detect_language(file_path: str | Path) -> str:
    """Detect programming language from file extension."""
    suffix = Path(file_path).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(suffix, "unknown")


# ---------------------------------------------------------------------------
# Tree-Sitter Extractors
# ---------------------------------------------------------------------------

# Try to import tree-sitter; fall back to regex if unavailable
_HAS_TREE_SITTER = False
try:
    import tree_sitter_python as tspython
    import tree_sitter as ts  # noqa: F811

    _HAS_TREE_SITTER = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Regex-based Extractor (fallback for all languages)
# ---------------------------------------------------------------------------

class RegexSymbolExtractor:
    """Regex-based symbol extraction as fallback for languages without tree-sitter."""

    # Patterns per language
    PATTERNS: dict[str, list[tuple[str, str, int]]] = {
        "python": [
            # (pattern, kind, regex_flags) — re.MULTILINE needed for indented defs/classes
            # Use [ \t]* instead of \s* to avoid matching newlines as whitespace
            (r"^[ \t]*def\s+(\w+)\s*\(([^)]*)\)", "function", re.MULTILINE),
            (r"^[ \t]*class\s+(\w+)", "class", re.MULTILINE),
            (r"^[ \t]*async\s+def\s+(\w+)\s*\(([^)]*)\)", "function", re.MULTILINE),
            (r"^[ \t]*(\w+)\s*[:=]\s*(?:.+)", "variable", re.MULTILINE),
        ],
        "typescript": [
            (r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"(?:export\s+)?class\s+(\w+)", "class", 0),
            (r"(?:export\s+)?interface\s+(\w+)", "interface", 0),
            (r"(?:export\s+)?type\s+(\w+)\s*=", "type", 0),
            (r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=]", "variable", 0),
            (r"(?:export\s+)?enum\s+(\w+)", "enum", 0),
        ],
        "javascript": [
            (r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"(?:export\s+)?class\s+(\w+)", "class", 0),
            (r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=]", "variable", 0),
        ],
        "go": [
            (r"func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"type\s+(\w+)\s+struct", "class", 0),
            (r"type\s+(\w+)\s+interface", "interface", 0),
            (r"var\s+(\w+)\s+", "variable", 0),
            (r"const\s+(\w+)\s+", "const", 0),
        ],
        "rust": [
            (r"(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"(?:pub\s+)?struct\s+(\w+)", "class", 0),
            (r"(?:pub\s+)?enum\s+(\w+)", "enum", 0),
            (r"(?:pub\s+)?trait\s+(\w+)", "interface", 0),
            (r"(?:pub\s+)?impl\s+(\w+)", "class", 0),
            (r"(?:pub\s+)?(?:static\s+)?(?:let|const)\s+(\w+)", "variable", 0),
        ],
        "java": [
            (r"(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?\w+\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"(?:public\s+)?class\s+(\w+)", "class", 0),
            (r"(?:public\s+)?interface\s+(\w+)", "interface", 0),
            (r"(?:public\s+)?enum\s+(\w+)", "enum", 0),
        ],
        "c": [
            (r"\w+\s+(\w+)\s*\(([^)]*)\)\s*\{", "function", 0),
            (r"struct\s+(\w+)", "class", 0),
            (r"enum\s+(\w+)", "enum", 0),
        ],
        "c++": [
            (r"(?:virtual\s+)?\w+\s+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{", "function", 0),
            (r"class\s+(\w+)", "class", 0),
            (r"struct\s+(\w+)", "class", 0),
            (r"enum\s+(?:class\s+)?(\w+)", "enum", 0),
        ],
        "c#": [
            (r"(?:public|private|protected|internal)?\s*(?:static\s+)?\w+\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"(?:public\s+)?class\s+(\w+)", "class", 0),
            (r"(?:public\s+)?interface\s+(\w+)", "interface", 0),
            (r"(?:public\s+)?enum\s+(\w+)", "enum", 0),
        ],
        "ruby": [
            (r"def\s+(?:self\.)?(\w+)(?:\(([^)]*)\))?", "function", 0),
            (r"class\s+(\w+)", "class", 0),
            (r"module\s+(\w+)", "module", 0),
        ],
        "php": [
            (r"(?:public|private|protected)?\s*(?:static\s+)?function\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"class\s+(\w+)", "class", 0),
            (r"interface\s+(\w+)", "interface", 0),
        ],
        "swift": [
            (r"func\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"class\s+(\w+)", "class", 0),
            (r"struct\s+(\w+)", "class", 0),
            (r"protocol\s+(\w+)", "interface", 0),
            (r"enum\s+(\w+)", "enum", 0),
        ],
        "kotlin": [
            (r"(?:suspend\s+)?fun\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"class\s+(\w+)", "class", 0),
            (r"interface\s+(\w+)", "interface", 0),
            (r"object\s+(\w+)", "class", 0),
        ],
        "scala": [
            (r"def\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"class\s+(\w+)", "class", 0),
            (r"object\s+(\w+)", "class", 0),
            (r"trait\s+(\w+)", "interface", 0),
        ],
        "lua": [
            (r"function\s+(\w+)\s*\(([^)]*)\)", "function", 0),
            (r"(\w+)\s*=\s*function\s*\(([^)]*)\)", "function", 0),
        ],
        "bash": [
            (r"^(\w+)\s*\(\s*\)\s*\{", "function", re.MULTILINE),
            (r"function\s+(\w+)\s*\{", "function", 0),
        ],
        "sql": [
            (r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(\w+)", "function", re.IGNORECASE),
            (r"CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+(\w+)", "function", re.IGNORECASE),
            (r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", "class", re.IGNORECASE),
            (r"CREATE\s+VIEW\s+(\w+)", "class", re.IGNORECASE),
        ],
    }

    @classmethod
    def extract(cls, source: str, language: str, file_path: str = "") -> list[Symbol]:
        """Extract symbols using regex patterns for the given language."""
        patterns = cls.PATTERNS.get(language, cls.PATTERNS.get("python", []))
        symbols: list[Symbol] = []
        seen: set[tuple[str, str, int]] = set()

        for pattern, kind, flags in patterns:
            for match in re.finditer(pattern, source, flags):
                name = match.group(1)
                line_start = source[: match.start()].count("\n") + 1
                # line_end = line of the last character in the match
                match_end_pos = match.end()
                line_end = source[:match_end_pos].count("\n") + 1
                if line_end < line_start:
                    line_end = line_start

                # Deduplicate by (name, kind, line_start)
                key = (name, kind, line_start)
                if key in seen:
                    continue
                seen.add(key)

                # Extract signature if available
                signature = None
                if len(match.groups()) >= 2 and match.group(2) is not None:
                    signature = f"{name}({match.group(2)})"

                symbols.append(
                    Symbol(
                        name=name,
                        kind=kind,
                        line_start=line_start,
                        line_end=line_end,
                        signature=signature,
                        language=language,
                        is_exported=not name.startswith("_"),
                    )
                )

        return symbols


# ---------------------------------------------------------------------------
# Tree-Sitter Extractor (when available)
# ---------------------------------------------------------------------------

class TreeSitterExtractor:
    """Tree-sitter based symbol extraction for supported languages."""

    # Language name → (tree_sitter_language_module, node_type_for_symbols)
    SUPPORTED: dict[str, str] = {
        "python": "tree_sitter_python",
        "typescript": "tree_sitter_typescript",
        "javascript": "tree_sitter_javascript",
        "go": "tree_sitter_go",
        "rust": "tree_sitter_rust",
        "java": "tree_sitter_java",
        "c": "tree_sitter_c",
        "c++": "tree_sitter_cpp",
        "c#": "tree_sitter_c_sharp",
        "ruby": "tree_sitter_ruby",
        "php": "tree_sitter_php",
        "swift": "tree_sitter_swift",
        "kotlin": "tree_sitter_kotlin",
        "bash": "tree_sitter_bash",
    }

    # Node types that represent symbol definitions per language
    SYMBOL_NODE_TYPES: dict[str, dict[str, str]] = {
        "python": {
            "function_definition": "function",
            "class_definition": "class",
            "assignment": "variable",
            "decorated_definition": "function",  # needed for @decorator-style functions
        },
        "typescript": {
            "function_declaration": "function",
            "method_definition": "method",
            "class_declaration": "class",
            "interface_declaration": "interface",
            "type_alias_declaration": "type",
            "enum_declaration": "enum",
            "variable_declarator": "variable",
            "lexical_declaration": "variable",
        },
        "javascript": {
            "function_declaration": "function",
            "class_declaration": "class",
            "variable_declarator": "variable",
            "lexical_declaration": "variable",
        },
        "go": {
            "function_declaration": "function",
            "method_declaration": "method",
            "type_declaration": "type",
            "var_declaration": "variable",
            "const_declaration": "const",
        },
        "rust": {
            "function_item": "function",
            "struct_item": "class",
            "enum_item": "enum",
            "trait_item": "interface",
            "impl_item": "class",
            "const_item": "const",
        },
    }

    @classmethod
    def extract(cls, source: bytes | str, language: str, file_path: str = "") -> list[Symbol]:
        """Extract symbols using tree-sitter for the given language."""
        if not _HAS_TREE_SITTER or language not in cls.SUPPORTED:
            return RegexSymbolExtractor.extract(
                source if isinstance(source, str) else source.decode("utf-8", errors="replace"),
                language,
                file_path,
            )

        try:
            # Import language-specific parser
            module_name = cls.SUPPORTED[language]
            lang_module = __import__(module_name, fromlist=["language"])

            parser = ts.Parser(ts.Language(lang_module.language()))

            if isinstance(source, str):
                source = source.encode("utf-8")

            tree = parser.parse(source)
            source_str = source.decode("utf-8", errors="replace")

            symbols: list[Symbol] = []
            node_types = cls.SYMBOL_NODE_TYPES.get(language, {})

            def _walk(node):
                if node.type in node_types:
                    kind = node_types[node.type]
                    name = cls._extract_name(node, source_str, language)
                    if name:
                        line_start = node.start_point[0] + 1
                        line_end = node.end_point[0] + 1
                        symbols.append(
                            Symbol(
                                name=name,
                                kind=kind,
                                line_start=line_start,
                                line_end=line_end,
                                language=language,
                                is_exported=not name.startswith("_"),
                            )
                        )
                for child in node.children:
                    _walk(child)

            _walk(tree.root_node)
            return symbols

        except Exception:
            # Fall back to regex
            return RegexSymbolExtractor.extract(
                source if isinstance(source, str) else source.decode("utf-8", errors="replace"),
                language,
                file_path,
            )

    @classmethod
    def _extract_name(cls, node, source: str, language: str) -> Optional[str]:
        """Extract the symbol name from a tree-sitter node."""
        # Look for a child node that contains the name
        name_children = {
            "python": ["name"],
            "typescript": ["name"],
            "javascript": ["name"],
            "go": ["name"],
            "rust": ["name"],
            "java": ["name"],
            "c": ["declarator", "name"],
            "c++": ["declarator", "name"],
            "c#": ["name"],
        }

        child_names = name_children.get(language, ["name"])
        for child in node.children:
            if child.type in child_names:
                # Get the text for this child
                start_byte = child.start_byte
                end_byte = child.end_byte
                return source[start_byte:end_byte]
            # Try nested children
            for grandchild in child.children:
                if grandchild.type in child_names:
                    return source[grandchild.start_byte : grandchild.end_byte]

        return None


# ---------------------------------------------------------------------------
# Unified Extractor Interface
# ---------------------------------------------------------------------------

class SymbolExtractor:
    """Unified symbol extraction interface.

    Automatically selects tree-sitter (when available) or regex fallback
    based on the language and installed packages.
    """

    @staticmethod
    def extract(source: str, language: str, file_path: str = "") -> list[Symbol]:
        """Extract all symbols from source code."""
        if _HAS_TREE_SITTER and language in TreeSitterExtractor.SUPPORTED:
            return TreeSitterExtractor.extract(source, language, file_path)
        return RegexSymbolExtractor.extract(source, language, file_path)

    @staticmethod
    def from_file(file_path: str | Path) -> list[Symbol]:
        """Extract symbols from a file on disk."""
        path = Path(file_path)
        language = detect_language(path)
        if language == "unknown":
            return []

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []

        return SymbolExtractor.extract(source, language, str(path))


# ---------------------------------------------------------------------------
# Description Extraction (from comments/docstrings)
# ---------------------------------------------------------------------------

class DescriptionExtractor:
    """Extract human-readable descriptions from comments and docstrings."""

    DOCSTRING_PATTERNS: dict[str, re.Pattern] = {
        "python": re.compile(r'"""(.*?)"""', re.DOTALL),
        "typescript": re.compile(r"/\*\*(.*?)\*/", re.DOTALL),
        "javascript": re.compile(r"/\*\*(.*?)\*/", re.DOTALL),
        "go": re.compile(r"//\s*(\w+)\s+(.*?)(?:\n|$)", re.MULTILINE),
        "rust": re.compile(r"///\s*(.*?)(?:\n|$)", re.MULTILINE),
        "java": re.compile(r"/\*\*(.*?)\*/", re.DOTALL),
        "c": re.compile(r"/\*\*(.*?)\*/", re.DOTALL),
        "c++": re.compile(r"/\*\*(.*?)\*/", re.DOTALL),
        "c#": re.compile(r"///\s*(.*?)(?:\n|$)", re.MULTILINE),
        "ruby": re.compile(r"#\s*(.*?)(?:\n|$)", re.MULTILINE),
    }

    @classmethod
    def extract_file_description(cls, source: str, language: str) -> Optional[str]:
        """Extract a file-level description from the first comment block."""
        pattern = cls.DOCSTRING_PATTERNS.get(language)
        if pattern is None:
            return None

        match = pattern.search(source)
        if match:
            desc = match.group(1).strip()
            # Clean up common prefixes
            lines = desc.split("\n")
            cleaned = []
            for line in lines:
                line = line.strip().lstrip("*").lstrip("/").lstrip("#").strip()
                if line and not line.startswith("@"):
                    cleaned.append(line)
            return " ".join(cleaned[:3])[:500] if cleaned else None
        return None

    @classmethod
    def extract_symbol_description(
        cls, source: str, symbol: Symbol, language: str
    ) -> Optional[str]:
        """Extract a description for a specific symbol."""
        # Get the lines just before the symbol
        symbol_lines = source.split("\n")
        start = max(0, symbol.line_start - 10)
        before = symbol_lines[start : symbol.line_start - 1]

        # Look for a comment block immediately before the symbol
        comment_lines = []
        for line in reversed(before):
            stripped = line.strip()
            if language == "python":
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    comment_lines.insert(0, stripped.strip('"\'').strip())
                    break
                if stripped.startswith("#"):
                    comment_lines.insert(0, stripped.lstrip("#").strip())
                else:
                    break
            elif language in ("typescript", "javascript", "java", "c", "c++"):
                if stripped.startswith("//") or stripped.startswith("*"):
                    comment_lines.insert(0, stripped.lstrip("/").lstrip("*").strip())
                elif stripped.endswith("*/"):
                    comment_lines.insert(0, stripped.rstrip("*/").strip())
                    break
                else:
                    break
            elif language in ("go", "rust", "c#"):
                if stripped.startswith("//"):
                    comment_lines.insert(0, stripped.lstrip("/").strip())
                else:
                    break
            elif language == "ruby":
                if stripped.startswith("#"):
                    comment_lines.insert(0, stripped.lstrip("#").strip())
                else:
                    break

        if comment_lines:
            return " ".join(comment_lines)[:500]
        return None