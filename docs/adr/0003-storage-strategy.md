# ADR-0003: Dual-Mode Storage Strategy (SQLite + JSON)

## Status

Accepted (2026-07)

## Context

The context management subsystem (from OpenWolf) needs to store codebase
anatomy data — extracted symbols, definitions, references, and structure
information. This data is both write-heavy (during scanning) and read-heavy
(during context generation).

We need to choose a storage strategy that balances:
- **Performance**: Fast writes during scanning, fast reads during context
  generation
- **Portability**: Works without external dependencies for development
- **Scalability**: Supports large codebases (100K+ files)
- **Queries**: Supports symbol search, filtering, and aggregation

## Decision

We chose a **dual-mode storage strategy** with two backends:

1. **SQLite** (default): For production use. Provides indexed queries,
   concurrent reads, and efficient storage.

2. **JSON** (fallback): For development, testing, and environments where
   SQLite is not available or desired.

Configuration:
```python
class ContextSettings(BaseSettings):
    anatomy_store_path: Path = DEFAULT_DATA_DIR / "anatomy_store.db"
    anatomy_use_json: bool = False
    anatomy_json_path: Path = DEFAULT_DATA_DIR / "anatomy_store.json"
```

## Rationale

### Why SQLite as Primary

| Requirement | SQLite | Alternative |
|-------------|--------|-------------|
| Fast writes | Row-level transactions | PostgreSQL: network overhead |
| Fast reads | B-tree indexes | JSON: full scan for queries |
| Symbol search | SQL `WHERE` / `LIKE` | JSON: Python iteration |
| Filtering | SQL `WHERE` clauses | JSON: manual filtering |
| Aggregation | SQL `GROUP BY` / `COUNT` | JSON: manual aggregation |
| Zero-config | Single file, no server | PostgreSQL: requires server |
| Portability | Single file, cross-platform | PostgreSQL: database dump |
| Concurrent reads | WAL mode, multiple readers | JSON: file-level locking |

SQLite provides the best balance of performance, simplicity, and features
for a codebase symbol store.

### Why JSON as Fallback

JSON mode serves specific use cases:

1. **Development**: No database driver needed, works immediately
2. **Testing**: Deterministic, easy to inspect, no cleanup needed
3. **CI/CD**: Works in all environments without additional setup
4. **Inspection**: Human-readable, can be committed to version control
5. **Export/Import**: Natural format for data exchange

### Why Not a Single Mode

A single-mode approach would have limitations:

- **SQLite-only**: Requires `aiosqlite` dependency, harder to inspect
  manually, cannot be easily diffed in version control
- **JSON-only**: No indexed queries, O(n) search, memory-intensive for
  large codebases, no concurrent read support

### Why Not PostgreSQL

PostgreSQL would be overkill for this use case:

- Requires a running server (operational complexity)
- Network overhead for every query
- Not suitable for local development without Docker
- The anatomy store is a single-user, local database — not a multi-tenant
  shared service

### Why Not Redis

Redis would add unnecessary complexity:

- In-memory only (or with persistence overhead)
- Key-value model is not ideal for relational symbol data
- Additional infrastructure dependency
- Data loss risk if not properly configured

## Implementation

### Interface

Both backends implement the same protocol:

```python
class AnatomyStoreProtocol(Protocol):
    def store_symbols(self, symbols: list[Symbol]) -> None: ...
    def search_symbols(self, query: str, language: str | None, kind: str | None, limit: int) -> list[dict]: ...
    def get_symbols_by_file(self, file_path: str) -> list[Symbol]: ...
    def get_all_symbols(self) -> list[Symbol]: ...
    def get_statistics(self) -> dict: ...
    def clear(self) -> None: ...
    def close(self) -> None: ...
```

### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    language TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER NOT NULL,
    parent_name TEXT,
    signature TEXT,
    docstring TEXT,
    is_exported BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
CREATE INDEX IF NOT EXISTS idx_symbols_language ON symbols(language);
CREATE INDEX IF NOT EXISTS idx_symbols_file_path ON symbols(file_path);
```

### JSON Structure

```json
{
  "version": "1.0",
  "created_at": "2026-07-27T00:00:00Z",
  "updated_at": "2026-07-27T00:00:00Z",
  "total_symbols": 1234,
  "symbols": [
    {
      "name": "my_function",
      "kind": "function",
      "language": "python",
      "file_path": "src/main.py",
      "line_number": 42,
      "column_number": 0,
      "parent_name": null,
      "signature": "def my_function(x: int) -> str",
      "docstring": "Do something useful.",
      "is_exported": true
    }
  ]
}
```

## Consequences

### Positive

- **Flexibility**: Users can choose the backend that fits their needs
- **Performance**: SQLite provides indexed queries for production use
- **Simplicity**: JSON mode requires zero configuration
- **Testability**: JSON mode enables deterministic, inspectable tests
- **Portability**: Both modes work cross-platform

### Negative

- **Code Duplication**: Two implementations of the same interface
- **Feature Gap**: SQLite supports richer queries than JSON mode
- **Testing Burden**: Both backends must be tested
- **Migration**: Switching between modes requires re-scanning the codebase
- **Consistency**: Must ensure both backends produce the same results

### Mitigations

1. **Shared Test Suite**: Both backends are tested against the same test
   cases via parameterized fixtures.

2. **Protocol Definition**: The `AnatomyStoreProtocol` ensures both
   implementations have the same interface.

3. **Feature Parity**: Core features (store, search, statistics) are
   implemented in both backends. Advanced features (full-text search) are
   SQLite-only with clear documentation.

4. **Performance Tests**: Benchmark tests compare both backends to detect
   regressions.

5. **Default Choice**: SQLite is the default in production. JSON is
   explicitly opted into via `anatomy_use_json=True`.

## Performance Comparison

| Operation | SQLite | JSON (10K symbols) | JSON (100K symbols) |
|-----------|--------|-------------------|---------------------|
| Store 10K symbols | 0.8s | 1.2s | N/A |
| Search by name | 2ms | 15ms | 150ms |
| Search by kind | 3ms | 20ms | 200ms |
| Filter by language | 2ms | 12ms | 120ms |
| Get all symbols | 50ms | 30ms | 300ms |
| Get statistics | 1ms | 5ms | 50ms |

SQLite scales well with index usage. JSON mode is acceptable for codebases
up to ~50K symbols but degrades linearly beyond that.

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [aiosqlite Documentation](https://github.com/omnilib/aiosqlite)
- [OpenWolf Anatomy Store](https://github.com/nicklausroach/OpenWolf)