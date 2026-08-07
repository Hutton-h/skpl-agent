"""Tests for AnatomyStore: SQLite and JSON backends."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from skpl_agent.context.anatomy_store import (
    AnatomyStore,
    AnatomyStoreMode,
    JSONAnatomyStore,
    SQLiteAnatomyStore,
)
from skpl_agent.context.symbol_extractor import Symbol
from skpl_agent.context.types import SymbolKind


@pytest.fixture
def sample_symbol() -> Symbol:
    """Create a sample symbol for testing."""
    return Symbol(
        name="test_function",
        kind=SymbolKind.FUNCTION,
        line_start=10,
        line_end=15,
        signature="def test_function(x: int) -> str",
        description="A test function",
        parent="TestClass",
        language="python",
        is_exported=True,
    )


class TestSQLiteStore:
    """SQLite-backed anatomy store tests."""

    @pytest.fixture
    def store(self) -> SQLiteAnatomyStore:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = SQLiteAnatomyStore(db_path)
        yield store
        store.close()
        Path(db_path).unlink(missing_ok=True)

    def test_upsert_symbol(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Inserts a symbol into the store."""
        store.upsert_symbol("test.py", sample_symbol)
        symbols = store.get_file_symbols("test.py")
        assert len(symbols) == 1
        assert symbols[0]["name"] == "test_function"

    def test_upsert_updates_existing(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Upserting an existing symbol updates it."""
        store.upsert_symbol("test.py", sample_symbol)
        sample_symbol.description = "Updated description"
        store.upsert_symbol("test.py", sample_symbol)
        symbols = store.get_file_symbols("test.py")
        assert len(symbols) == 1
        assert symbols[0]["description"] == "Updated description"

    def test_delete_file_symbols(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Deletes all symbols for a file."""
        store.upsert_symbol("test.py", sample_symbol)
        store.delete_file_symbols("test.py")
        symbols = store.get_file_symbols("test.py")
        assert len(symbols) == 0

    def test_get_file_symbols_empty(self, store: SQLiteAnatomyStore) -> None:
        """Returns empty list for unregistered file."""
        symbols = store.get_file_symbols("nonexistent.py")
        assert symbols == []

    def test_search_symbols_by_name(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Searches symbols by name."""
        store.upsert_symbol("test.py", sample_symbol)
        results = store.search_symbols("test_function")
        assert len(results) >= 1
        assert results[0]["name"] == "test_function"

    def test_search_symbols_no_match(self, store: SQLiteAnatomyStore) -> None:
        """Returns empty list when no match found."""
        results = store.search_symbols("nonexistent")
        assert results == []

    def test_search_by_language(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Filters search by language."""
        store.upsert_symbol("test.py", sample_symbol)
        results = store.search_symbols("test", language="python")
        assert len(results) >= 1

        results = store.search_symbols("test", language="javascript")
        assert len(results) == 0

    def test_search_limit(self, store: SQLiteAnatomyStore) -> None:
        """Respects search result limit."""
        for i in range(10):
            sym = Symbol(
                name=f"func_{i}",
                kind=SymbolKind.FUNCTION,
                line_start=i,
                line_end=i + 1,
                language="python",
            )
            store.upsert_symbol(f"file_{i}.py", sym)

        results = store.search_symbols("func", limit=5)
        assert len(results) <= 5

    def test_get_stats(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Returns store statistics."""
        store.upsert_symbol("test.py", sample_symbol)
        stats = store.get_stats()
        assert stats["total_symbols"] == 1
        assert stats["total_files"] == 1
        assert "python" in stats["languages"]
        assert stats["backend"] == "sqlite"

    def test_clear(self, store: SQLiteAnatomyStore, sample_symbol: Symbol) -> None:
        """Clears all symbols."""
        store.upsert_symbol("test.py", sample_symbol)
        store.clear()
        stats = store.get_stats()
        assert stats["total_symbols"] == 0

    def test_multiple_files(self, store: SQLiteAnatomyStore) -> None:
        """Handles symbols across multiple files."""
        for i in range(3):
            sym = Symbol(
                name=f"func_{i}",
                kind=SymbolKind.FUNCTION,
                line_start=i,
                line_end=i + 1,
                language="python",
            )
            store.upsert_symbol(f"file_{i}.py", sym)

        stats = store.get_stats()
        assert stats["total_symbols"] == 3
        assert stats["total_files"] == 3


class TestJSONStore:
    """JSON-backed anatomy store tests."""

    @pytest.fixture
    def store(self) -> JSONAnatomyStore:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        store = JSONAnatomyStore(json_path)
        yield store
        store.close()
        Path(json_path).unlink(missing_ok=True)

    def test_upsert_symbol(self, store: JSONAnatomyStore, sample_symbol: Symbol) -> None:
        """Inserts a symbol into the JSON store."""
        store.upsert_symbol("test.py", sample_symbol)
        symbols = store.get_file_symbols("test.py")
        assert len(symbols) == 1
        assert symbols[0]["name"] == "test_function"

    def test_upsert_updates_existing(self, store: JSONAnatomyStore, sample_symbol: Symbol) -> None:
        """Upserting updates existing symbol."""
        store.upsert_symbol("test.py", sample_symbol)
        sample_symbol.description = "Updated"
        store.upsert_symbol("test.py", sample_symbol)
        symbols = store.get_file_symbols("test.py")
        assert len(symbols) == 1
        assert symbols[0]["description"] == "Updated"

    def test_delete_file_symbols(self, store: JSONAnatomyStore, sample_symbol: Symbol) -> None:
        """Deletes all symbols for a file."""
        store.upsert_symbol("test.py", sample_symbol)
        store.delete_file_symbols("test.py")
        symbols = store.get_file_symbols("test.py")
        assert len(symbols) == 0

    def test_get_file_symbols_empty(self, store: JSONAnatomyStore) -> None:
        """Returns empty list for unknown file."""
        symbols = store.get_file_symbols("unknown.py")
        assert symbols == []

    def test_search_symbols(self, store: JSONAnatomyStore, sample_symbol: Symbol) -> None:
        """Searches symbols by name."""
        store.upsert_symbol("test.py", sample_symbol)
        results = store.search_symbols("test_function")
        assert len(results) >= 1

    def test_search_no_match(self, store: JSONAnatomyStore) -> None:
        """Returns empty list for no match."""
        results = store.search_symbols("nonexistent")
        assert results == []

    def test_get_stats(self, store: JSONAnatomyStore, sample_symbol: Symbol) -> None:
        """Returns store statistics."""
        store.upsert_symbol("test.py", sample_symbol)
        stats = store.get_stats()
        assert stats["total_symbols"] == 1
        assert stats["total_files"] == 1
        assert stats["backend"] == "json"

    def test_clear(self, store: JSONAnatomyStore, sample_symbol: Symbol) -> None:
        """Clears all symbols."""
        store.upsert_symbol("test.py", sample_symbol)
        store.clear()
        stats = store.get_stats()
        assert stats["total_symbols"] == 0

    def test_persistence(self, sample_symbol: Symbol) -> None:
        """Data persists across store instances."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name

        store1 = JSONAnatomyStore(json_path)
        store1.upsert_symbol("test.py", sample_symbol)
        store1.close()

        store2 = JSONAnatomyStore(json_path)
        symbols = store2.get_file_symbols("test.py")
        assert len(symbols) == 1
        assert symbols[0]["name"] == "test_function"
        store2.close()

        Path(json_path).unlink(missing_ok=True)


class TestAnatomyStoreFactory:
    """AnatomyStore factory tests."""

    def test_create_sqlite(self) -> None:
        """Creates SQLite store."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = AnatomyStore.create(AnatomyStoreMode.SQLITE, db_path)
        assert isinstance(store, SQLiteAnatomyStore)
        store.close()
        Path(db_path).unlink(missing_ok=True)

    def test_create_json(self) -> None:
        """Creates JSON store."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        store = AnatomyStore.create(AnatomyStoreMode.JSON, json_path)
        assert isinstance(store, JSONAnatomyStore)
        store.close()
        Path(json_path).unlink(missing_ok=True)

    def test_create_invalid_mode(self) -> None:
        """Raises ValueError for invalid mode."""
        with pytest.raises(ValueError, match="Unknown anatomy store mode"):
            AnatomyStore.create("invalid", "/tmp/test.db")  # type: ignore