"""SQLite connection management and schema initialization.

Why this module exists:
- Centralizes connection creation so every caller gets the sqlite-vec
  extension pre-loaded (agents need vector search on every enrichment).
- Runs the schema.sql as an idempotent migration on startup.
- Creates the `memory_vec` virtual table (which requires the extension
  to already be loaded, so it cannot live in plain schema.sql).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import sqlite_vec

from app.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Embedding dimension for OpenAI text-embedding-3-small.
# Why 1536: OpenAI's small model outputs 1536-dim vectors. If we ever move to
# text-embedding-3-large (3072-dim), we bump this and re-embed memory.
EMBEDDING_DIM = 1536


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    """Row factory that returns dicts keyed by column name."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a sqlite3 connection with sqlite-vec loaded.

    Args:
        db_path: optional override; defaults to settings.db_path.
    Returns:
        An open sqlite3.Connection with:
          - foreign keys ON
          - sqlite-vec extension loaded
          - Row factory returning dicts
    """
    path = Path(db_path) if db_path is not None else get_settings().db_path
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    # Why check_same_thread=False + WAL: FastAPI runs handlers on a threadpool.
    # WAL + read-only queries from many threads is safe; writes serialize naturally.
    conn.row_factory = _row_to_dict

    # Load sqlite-vec — required before we can create or query memory_vec.
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, type_and_default: str) -> None:
    """Idempotent ADD COLUMN for existing DBs. CREATE TABLE IF NOT EXISTS
    doesn't add columns when the table already exists, so we run a small
    pragma check + ALTER TABLE for each column we've added since v1.
    """
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_and_default}")


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create the schema (idempotent) and return a ready-to-use connection.

    Safe to call on every process start — CREATE TABLE IF NOT EXISTS plus
    a handful of targeted ADD COLUMN migrations for tables that pre-date
    a newer column.  Also creates the memory_vec virtual table which
    depends on sqlite-vec.
    """
    conn = connect(db_path)

    # Run declarative schema.
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)

    # Post-v1 column migrations.
    _ensure_column(conn, "raw_emails", "is_web_form", "INTEGER NOT NULL DEFAULT 0")

    # Create vec0 virtual table — depends on sqlite-vec being loaded.
    # Why a separate table: vec0 is a virtual table backed by the extension;
    # it's keyed by memory_id so we can join back to memory on retrieval.
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec USING vec0(
            memory_id INTEGER PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIM}]
        )
        """
    )

    # Seed a default system_state kill switch if absent.
    conn.execute(
        "INSERT OR IGNORE INTO system_state(key, value) VALUES ('kill_switch','off')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO system_state(key, value) VALUES ('last_gmail_history_id','')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO system_state(key, value) VALUES ('daily_sent_count','0')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO system_state(key, value) VALUES ('daily_sent_date','')"
    )

    return conn


_SHARED_CONN: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    """Return a process-wide shared connection.

    Why shared: SQLite in WAL mode + check_same_thread=False allows one
    connection across FastAPI's threadpool. This keeps transactions simple
    and avoids per-request connect overhead.
    """
    global _SHARED_CONN
    if _SHARED_CONN is None:
        _SHARED_CONN = init_db()
    return _SHARED_CONN


# -- Convenience wrappers (thin) --

def execute(sql: str, params: Iterable[Any] | dict[str, Any] = ()) -> sqlite3.Cursor:
    """Execute a statement on the shared connection and return the cursor."""
    return get_conn().execute(sql, params)


def fetch_one(sql: str, params: Iterable[Any] | dict[str, Any] = ()) -> dict[str, Any] | None:
    """Return the first row as a dict, or None."""
    cur = get_conn().execute(sql, params)
    row = cur.fetchone()
    return row if row else None


def fetch_all(sql: str, params: Iterable[Any] | dict[str, Any] = ()) -> list[dict[str, Any]]:
    """Return all rows as a list of dicts."""
    cur = get_conn().execute(sql, params)
    return list(cur.fetchall())


def dumps(obj: Any) -> str:
    """JSON-serialize with sensible defaults for reasoning logs."""
    return json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))
