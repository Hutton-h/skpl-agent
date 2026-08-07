"""
Anatomy Store — Persistent storage for symbol and description indices.

Supports two modes:
- SQLite: For production use with concurrent access and querying
- JSON: For lightweight/embedded use cases

Both modes implement the same AnatomyStoreProtocol interface.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol

from skpl_agent.context.symbol_extractor import Symbol


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class AnatomyStoreMode(Enum):
    SQLITE = "sqlite"
    JSON = "json"


class AnatomyStoreProtocol(Protocol):
    """Protocol that all anatomy store backends must implement."""

    def upsert_symbol(self, file_path: str, symbol: Symbol) -> None: ...
    def delete_file_symbols(self, file_path: str) -> None: ...
    def get_file_symbols(self, file_path: str) -> list[dict]: ...
    def search_symbols(self, query: str, language: str | None = None) -> list[dict]: ...
    def get_stats(self) -> dict: ...
    def clear(self) -> None: ...
    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# SQLite Backend
# ---------------------------------------------------------------------------


class SQLiteAnatomyStore:
    """SQLite-backed anatomy store with WAL mode for concurrent access."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                language TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                signature TEXT,
                description TEXT,
                parent TEXT,
                is_exported INTEGER DEFAULT 0,
                token_count INTEGER,
                hash TEXT,
                scanned_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_path);
            CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
            CREATE INDEX IF NOT EXISTS idx_symbols_lang ON symbols(language);
            CREATE INDEX IF NOT EXISTS idx_symbols_hash ON symbols(hash);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_symbols_unique
                ON symbols(file_path, name, kind, line_start);
        """)
        conn.commit()

    def upsert_symbol(self, file_path: str, symbol: Symbol) -> None:
        """Insert or update a symbol."""
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        symbol_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO symbols (id, file_path, name, kind, language, line_start,
                line_end, signature, description, parent, is_exported, token_count,
                hash, scanned_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path, name, kind, line_start) DO UPDATE SET
                line_end = excluded.line_end,
                signature = excluded.signature,
                description = excluded.description,
                parent = excluded.parent,
                is_exported = excluded.is_exported,
                token_count = excluded.token_count,
                hash = excluded.hash,
                scanned_at = excluded.scanned_at,
                updated_at = excluded.updated_at
            """,
            (
                symbol_id,
                file_path,
                symbol.name,
                symbol.kind,
                symbol.language or "unknown",
                symbol.line_start,
                symbol.line_end,
                symbol.signature,
                symbol.description,
                symbol.parent,
                1 if symbol.is_exported else 0,
                None,
                None,
                now,
                now,
                now,
            ),
        )
        conn.commit()

    def delete_file_symbols(self, file_path: str) -> None:
        """Delete all symbols for a file."""
        conn = self._get_conn()
        conn.execute("DELETE FROM symbols WHERE file_path = ?", (file_path,))
        conn.commit()

    def get_file_symbols(self, file_path: str) -> list[dict]:
        """Get all symbols for a file."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM symbols WHERE file_path = ? ORDER BY line_start",
            (file_path,),
        ).fetchall()
        return [dict(row) for row in rows]

    def search_symbols(
        self, query: str, language: str | None = None, kind: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Search symbols by name, signature, or description."""
        conn = self._get_conn()
        sql = """
            SELECT * FROM symbols
            WHERE (name LIKE ? OR signature LIKE ? OR description LIKE ?)
        """
        params: list = [f"%{query}%", f"%{query}%", f"%{query}%"]

        if language:
            sql += " AND language = ?"
            params.append(language)
        if kind:
            sql += " AND kind = ?"
            params.append(kind)

        sql += " ORDER BY name LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get store statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        files = conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM symbols"
        ).fetchone()[0]
        langs = conn.execute(
            "SELECT language, COUNT(*) as cnt FROM symbols GROUP BY language ORDER BY cnt DESC"
        ).fetchall()

        return {
            "total_symbols": total,
            "total_files": files,
            "languages": {row["language"]: row["cnt"] for row in langs},
            "backend": "sqlite",
            "db_path": str(self.db_path),
        }

    def clear(self) -> None:
        """Clear all symbols."""
        conn = self._get_conn()
        conn.execute("DELETE FROM symbols")
        conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ---------------------------------------------------------------------------
# JSON Backend
# ---------------------------------------------------------------------------


class JSONAnatomyStore:
    """JSON file-backed anatomy store for lightweight use cases."""

    def __init__(self, json_path: str | Path):
        self.json_path = Path(json_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, list[dict]] = self._load()

    def _load(self) -> dict[str, list[dict]]:
        """Load data from JSON file."""
        if self.json_path.exists():
            try:
                return json.loads(self.json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}

    def _save(self) -> None:
        """Save data to JSON file."""
        with self._lock:
            self.json_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _symbol_to_dict(self, file_path: str, symbol: Symbol) -> dict:
        """Convert a Symbol to a dict for storage."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": str(uuid.uuid4()),
            "file_path": file_path,
            "name": symbol.name,
            "kind": symbol.kind,
            "language": symbol.language or "unknown",
            "line_start": symbol.line_start,
            "line_end": symbol.line_end,
            "signature": symbol.signature,
            "description": symbol.description,
            "parent": symbol.parent,
            "is_exported": symbol.is_exported,
            "scanned_at": now,
            "created_at": now,
            "updated_at": now,
        }

    def upsert_symbol(self, file_path: str, symbol: Symbol) -> None:
        """Insert or update a symbol."""
        with self._lock:
            if file_path not in self._data:
                self._data[file_path] = []

            # Check for existing symbol
            for i, existing in enumerate(self._data[file_path]):
                if (
                    existing["name"] == symbol.name
                    and existing["kind"] == symbol.kind
                    and existing["line_start"] == symbol.line_start
                ):
                    self._data[file_path][i] = self._symbol_to_dict(file_path, symbol)
                    break
            else:
                self._data[file_path].append(self._symbol_to_dict(file_path, symbol))

        self._save()

    def delete_file_symbols(self, file_path: str) -> None:
        """Delete all symbols for a file."""
        with self._lock:
            self._data.pop(file_path, None)
        self._save()

    def get_file_symbols(self, file_path: str) -> list[dict]:
        """Get all symbols for a file."""
        with self._lock:
            return self._data.get(file_path, [])

    def search_symbols(
        self, query: str, language: str | None = None, kind: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Search symbols by name, signature, or description."""
        results: list[dict] = []
        query_lower = query.lower()

        with self._lock:
            for file_path, symbols in self._data.items():
                for sym in symbols:
                    if (
                        query_lower in sym.get("name", "").lower()
                        or query_lower in sym.get("signature", "").lower()
                        or query_lower in sym.get("description", "").lower()
                    ):
                        if language and sym.get("language") != language:
                            continue
                        if kind and sym.get("kind") != kind:
                            continue
                        results.append(sym)
                        if len(results) >= limit:
                            return results

        return results

    def get_stats(self) -> dict:
        """Get store statistics."""
        with self._lock:
            total = sum(len(syms) for syms in self._data.values())
            files = len(self._data)
            lang_counts: dict[str, int] = {}
            for syms in self._data.values():
                for sym in syms:
                    lang = sym.get("language", "unknown")
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

        return {
            "total_symbols": total,
            "total_files": files,
            "languages": lang_counts,
            "backend": "json",
            "json_path": str(self.json_path),
        }

    def clear(self) -> None:
        """Clear all symbols."""
        with self._lock:
            self._data = {}
        self._save()

    def close(self) -> None:
        """Save and close (no-op for JSON store)."""
        self._save()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class AnatomyStore:
    """Factory for anatomy store backends."""

    @staticmethod
    def create(mode: AnatomyStoreMode, path: str | Path) -> AnatomyStoreProtocol:
        """Create an anatomy store instance."""
        if mode == AnatomyStoreMode.SQLITE:
            return SQLiteAnatomyStore(path)
        elif mode == AnatomyStoreMode.JSON:
            return JSONAnatomyStore(path)
        else:
            raise ValueError(f"Unknown anatomy store mode: {mode}")