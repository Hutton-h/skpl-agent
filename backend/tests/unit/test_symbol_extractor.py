"""Tests for SymbolExtractor: tree-sitter and regex extraction paths."""

import pytest
from skpl_agent.context.symbol_extractor import (
    Symbol,
    SymbolExtractor,
    RegexSymbolExtractor,
    detect_language,
    LANGUAGE_EXTENSIONS,
)


class TestDetectLanguage:
    """Language detection from file extensions."""

    def test_python_extensions(self):
        assert detect_language("test.py") == "python"
        assert detect_language("test.pyi") == "python"

    def test_typescript_extensions(self):
        assert detect_language("test.ts") == "typescript"
        assert detect_language("test.tsx") == "typescript"

    def test_javascript_extensions(self):
        assert detect_language("test.js") == "javascript"
        assert detect_language("test.jsx") == "javascript"
        assert detect_language("test.mjs") == "javascript"
        assert detect_language("test.cjs") == "javascript"

    def test_go_extensions(self):
        assert detect_language("test.go") == "go"

    def test_rust_extensions(self):
        assert detect_language("test.rs") == "rust"

    def test_java_extensions(self):
        assert detect_language("test.java") == "java"

    def test_c_cpp_extensions(self):
        assert detect_language("test.c") == "c"
        assert detect_language("test.h") == "c"
        assert detect_language("test.cpp") == "c++"
        assert detect_language("test.hpp") == "c++"

    def test_csharp_extensions(self):
        assert detect_language("test.cs") == "c#"

    def test_web_extensions(self):
        assert detect_language("test.html") == "html"
        assert detect_language("test.css") == "css"
        assert detect_language("test.scss") == "css"

    def test_data_extensions(self):
        assert detect_language("test.json") == "json"
        assert detect_language("test.yaml") == "yaml"
        assert detect_language("test.yml") == "yaml"
        assert detect_language("test.toml") == "toml"

    def test_unknown_extension(self):
        assert detect_language("test.xyz") == "unknown"
        assert detect_language("Makefile") == "unknown"

    def test_case_insensitive(self):
        assert detect_language("test.PY") == "python"
        assert detect_language("test.TS") == "typescript"

    def test_path_with_dirs(self):
        assert detect_language("/path/to/file.py") == "python"
        assert detect_language("src\\components\\test.tsx") == "typescript"


class TestRegexSymbolExtractorPython:
    """Regex-based extraction for Python source code."""

    def test_extract_function(self):
        source = "def hello(name):\n    return f'Hello {name}'"
        symbols = RegexSymbolExtractor.extract(source, "python")
        names = [s.name for s in symbols]
        assert "hello" in names

    def test_extract_class(self):
        source = "class MyClass:\n    pass"
        symbols = RegexSymbolExtractor.extract(source, "python")
        names = [s.name for s in symbols]
        assert "MyClass" in names

    def test_extract_async_function(self):
        source = "async def fetch_data(url):\n    return await get(url)"
        symbols = RegexSymbolExtractor.extract(source, "python")
        names = [s.name for s in symbols]
        assert "fetch_data" in names

    def test_deduplication(self):
        """Multiple patterns should not produce duplicate symbols."""
        source = "def hello():\n    pass\n\ndef hello():\n    pass"
        symbols = RegexSymbolExtractor.extract(source, "python")
        hello_symbols = [s for s in symbols if s.name == "hello"]
        assert len(hello_symbols) == 2  # different lines, legit

    def test_exported_flag(self):
        source = "def _private():\n    pass"
        symbols = RegexSymbolExtractor.extract(source, "python")
        assert len(symbols) == 1
        assert symbols[0].is_exported is False

    def test_line_numbers(self):
        source = "# comment\n\ndef hello():\n    pass\n"
        symbols = RegexSymbolExtractor.extract(source, "python")
        func = [s for s in symbols if s.name == "hello"][0]
        assert func.line_start == 3  # 1-indexed
        assert func.line_end >= 3

    def test_empty_source(self):
        symbols = RegexSymbolExtractor.extract("", "python")
        assert symbols == []

    def test_no_matches(self):
        source = "# just a comment"
        symbols = RegexSymbolExtractor.extract(source, "python")
        assert symbols == []


class TestRegexSymbolExtractorTypeScript:
    """Regex-based extraction for TypeScript source code."""

    def test_extract_function(self):
        source = "function greet(name: string): string {\n  return `Hello ${name}`;\n}"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "greet" in names

    def test_extract_export_function(self):
        source = "export function add(a: number, b: number): number {\n  return a + b;\n}"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "add" in names

    def test_extract_class(self):
        source = "class UserService {\n  private users: User[];\n}"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "UserService" in names

    def test_extract_interface(self):
        source = "interface IUser {\n  id: string;\n  name: string;\n}"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "IUser" in names

    def test_extract_type_alias(self):
        source = "type UserId = string;"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "UserId" in names

    def test_extract_enum(self):
        source = "enum Color { Red, Green, Blue }"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "Color" in names

    def test_extract_const(self):
        source = "const MAX_RETRIES = 3;"
        symbols = RegexSymbolExtractor.extract(source, "typescript")
        names = [s.name for s in symbols]
        assert "MAX_RETRIES" in names


class TestRegexSymbolExtractorGo:
    """Regex-based extraction for Go source code."""

    def test_extract_function(self):
        source = "func ProcessData(input string) error {\n  return nil\n}"
        symbols = RegexSymbolExtractor.extract(source, "go")
        names = [s.name for s in symbols]
        assert "ProcessData" in names

    def test_extract_method(self):
        source = "func (s *Server) Start() error {\n  return nil\n}"
        symbols = RegexSymbolExtractor.extract(source, "go")
        names = [s.name for s in symbols]
        assert "Start" in names

    def test_extract_struct(self):
        source = "type Config struct {\n  Host string\n  Port int\n}"
        symbols = RegexSymbolExtractor.extract(source, "go")
        names = [s.name for s in symbols]
        assert "Config" in names

    def test_extract_interface(self):
        source = "type Reader interface {\n  Read(p []byte) (n int, err error)\n}"
        symbols = RegexSymbolExtractor.extract(source, "go")
        names = [s.name for s in symbols]
        assert "Reader" in names


class TestRegexSymbolExtractorRust:
    """Regex-based extraction for Rust source code."""

    def test_extract_function(self):
        source = "fn main() {\n    println!(\"Hello\");\n}"
        symbols = RegexSymbolExtractor.extract(source, "rust")
        names = [s.name for s in symbols]
        assert "main" in names

    def test_extract_pub_function(self):
        source = "pub fn process(data: &str) -> Result<(), Error> {\n    Ok(())\n}"
        symbols = RegexSymbolExtractor.extract(source, "rust")
        names = [s.name for s in symbols]
        assert "process" in names

    def test_extract_struct(self):
        source = "pub struct Person {\n    name: String,\n    age: u32,\n}"
        symbols = RegexSymbolExtractor.extract(source, "rust")
        names = [s.name for s in symbols]
        assert "Person" in names

    def test_extract_enum(self):
        source = "pub enum Status {\n    Active,\n    Inactive,\n}"
        symbols = RegexSymbolExtractor.extract(source, "rust")
        names = [s.name for s in symbols]
        assert "Status" in names

    def test_extract_trait(self):
        source = "pub trait Display {\n    fn fmt(&self) -> String;\n}"
        symbols = RegexSymbolExtractor.extract(source, "rust")
        names = [s.name for s in symbols]
        assert "Display" in names


class TestRegexSymbolExtractorSQL:
    """Regex-based extraction for SQL source code."""

    def test_extract_create_function(self):
        source = "CREATE OR REPLACE FUNCTION calculate_total() RETURNS INTEGER AS $$"
        symbols = RegexSymbolExtractor.extract(source, "sql")
        names = [s.name for s in symbols]
        assert "calculate_total" in names

    def test_extract_create_table(self):
        source = "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY)"
        symbols = RegexSymbolExtractor.extract(source, "sql")
        names = [s.name for s in symbols]
        assert "users" in names

    def test_extract_create_view(self):
        source = "CREATE VIEW active_users AS SELECT * FROM users WHERE active = true"
        symbols = RegexSymbolExtractor.extract(source, "sql")
        names = [s.name for s in symbols]
        assert "active_users" in names


class TestSymbolExtractorUnified:
    """Unified SymbolExtractor interface (auto-selects tree-sitter or regex)."""

    def test_extract_python(self):
        source = "def hello():\n    pass\n\nclass World:\n    pass"
        symbols = SymbolExtractor.extract(source, "python")
        assert len(symbols) >= 2

    def test_extract_unknown_language(self):
        source = "some unknown content"
        symbols = SymbolExtractor.extract(source, "unknown")
        assert symbols == []

    def test_symbol_dataclass(self):
        sym = Symbol(
            name="test_func",
            kind="function",
            line_start=10,
            line_end=15,
            language="python",
            is_exported=True,
        )
        assert sym.name == "test_func"
        assert sym.kind == "function"
        assert sym.line_start == 10
        assert sym.line_end == 15
        assert sym.signature is None
        assert sym.description is None

    def test_symbol_hash(self):
        sym1 = Symbol(name="f", kind="function", line_start=1, line_end=1)
        sym2 = Symbol(name="f", kind="function", line_start=1, line_end=1)
        assert hash(sym1) == hash(sym2)

    def test_symbol_hash_different(self):
        sym1 = Symbol(name="f", kind="function", line_start=1, line_end=1)
        sym2 = Symbol(name="f", kind="function", line_start=2, line_end=2)
        assert hash(sym1) != hash(sym2)


class TestLanguageExtensionCoverage:
    """Ensure all expected languages have extension mappings."""

    def test_common_languages_mapped(self):
        expected = {
            "python": ".py",
            "typescript": ".ts",
            "javascript": ".js",
            "go": ".go",
            "rust": ".rs",
            "java": ".java",
            "c": ".c",
            "c++": ".cpp",
            "c#": ".cs",
            "ruby": ".rb",
            "php": ".php",
            "swift": ".swift",
            "kotlin": ".kt",
            "scala": ".scala",
            "lua": ".lua",
            "bash": ".sh",
            "sql": ".sql",
            "html": ".html",
            "css": ".css",
            "json": ".json",
            "yaml": ".yaml",
            "markdown": ".md",
        }
        for lang, ext in expected.items():
            assert ext in LANGUAGE_EXTENSIONS, f"Missing extension for {lang}"
            assert LANGUAGE_EXTENSIONS[ext] == lang, f"Wrong mapping for {ext}"