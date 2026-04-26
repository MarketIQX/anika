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


def _migrate_classifications_check_constraint(conn: sqlite3.Connection) -> None:
    """Phase 1B Cluster 7f migration.

    The classifications.category CHECK constraint was originally written for
    a 6-category list (new_enquiry, existing_client, sensitive, automated,
    spam, other). Phase 1B added 'recruitment_enquiry' and 'vendor_pitch' to
    the Pydantic Category Literal but the DB CHECK was never updated.

    This migration rewrites the table with the expanded CHECK if the live
    schema still has the old one. Idempotent: skipped after the first run.

    SQLite has no ALTER TABLE ... DROP CHECK, so we rebuild via the standard
    "create new, copy, drop, rename" pattern.

    SAFETY (Option α — landed in Cluster 7f):
      - PRAGMA foreign_keys = OFF must happen OUTSIDE a transaction
        (SQLite ignores the pragma mid-transaction).
      - The rebuild itself runs inside an explicit BEGIN/COMMIT so any
        failure (CREATE / INSERT / DROP / RENAME / index recreation) rolls
        back atomically — we never end up with both old and new tables, or
        with the old table dropped before rename succeeded.
      - Pre-INSERT and post-RENAME row-count assertions: the migration
        REFUSES to commit if any row was lost in flight.
      - We use individual conn.execute() calls (not executescript) because
        executescript auto-commits any open transaction on entry, which
        would defeat the wrapper.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='classifications'"
    ).fetchone()
    if not row:
        return  # fresh DB, classifications doesn't exist yet
    current_sql = row["sql"] if isinstance(row, dict) else row[0]
    if "recruitment_enquiry" in (current_sql or ""):
        return  # already migrated — idempotent

    pre_row = conn.execute("SELECT COUNT(*) AS n FROM classifications").fetchone()
    pre_count = pre_row["n"] if isinstance(pre_row, dict) else pre_row[0]

    # FK off must be set OUTSIDE a transaction. SQLite docs:
    #   "It is not possible to enable or disable foreign key support in the
    #    middle of a multi-statement transaction."
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            conn.execute("""
                CREATE TABLE classifications_new (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id     INTEGER NOT NULL REFERENCES raw_emails(id) ON DELETE CASCADE,
                    category     TEXT NOT NULL CHECK (category IN (
                        'new_enquiry','existing_client','sensitive',
                        'recruitment_enquiry','vendor_pitch',
                        'automated','spam','other'
                    )),
                    confidence   REAL NOT NULL,
                    reasoning    TEXT,
                    model        TEXT NOT NULL,
                    prompt_version INTEGER,
                    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                )
            """)
            conn.execute("""
                INSERT INTO classifications_new
                    SELECT id, email_id, category, confidence, reasoning, model,
                           prompt_version, created_at FROM classifications
            """)
            mid_row = conn.execute(
                "SELECT COUNT(*) AS n FROM classifications_new"
            ).fetchone()
            mid_count = mid_row["n"] if isinstance(mid_row, dict) else mid_row[0]
            if mid_count != pre_count:
                raise RuntimeError(
                    f"classifications migration aborted: INSERT lost rows "
                    f"(pre={pre_count}, new={mid_count})"
                )
            conn.execute("DROP TABLE classifications")
            conn.execute("ALTER TABLE classifications_new RENAME TO classifications")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_classifications_email "
                "ON classifications(email_id)"
            )
            post_row = conn.execute(
                "SELECT COUNT(*) AS n FROM classifications"
            ).fetchone()
            post_count = post_row["n"] if isinstance(post_row, dict) else post_row[0]
            if post_count != pre_count:
                raise RuntimeError(
                    f"classifications migration aborted: post-rename count "
                    f"diverged (pre={pre_count}, post={post_count})"
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


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

    # Post-v1 column migrations. Every column declared in schema.sql AFTER its
    # CREATE TABLE was first shipped needs a matching ALTER TABLE here, so
    # databases created on an older schema get the column on next boot.
    # Phase 1A / web-form era:
    _ensure_column(conn, "raw_emails", "is_web_form", "INTEGER NOT NULL DEFAULT 0")
    # Phase 1B Cluster 7f migration — expand classifications.category CHECK
    # to include recruitment_enquiry + vendor_pitch (must run BEFORE any
    # downstream code attempts to insert those values).
    _migrate_classifications_check_constraint(conn)

    # Phase 1B Cluster 2 — promoted from runtime ALTERs in scratch scripts.
    # NOTE: types here intentionally OMIT `NOT NULL` — they must match the live
    # DB shape produced by the original ALTER TABLE statements (which SQLite
    # always allows to be nullable). Anything stricter would mean the schema
    # describes one shape and the live DB has another.
    _ensure_column(conn, "drafts", "cognitive_state", "TEXT DEFAULT NULL")
    _ensure_column(conn, "drafts", "voice_coverage_count", "INTEGER DEFAULT 0")
    _ensure_column(conn, "memory", "is_active", "INTEGER DEFAULT 1")
    # knowledge_library — purpose-classification columns:
    _ensure_column(conn, "knowledge_library", "purpose", "TEXT DEFAULT 'voice_example'")
    _ensure_column(conn, "knowledge_library", "anika_proposed_purpose", "TEXT DEFAULT NULL")
    _ensure_column(conn, "knowledge_library", "anika_proposed_confidence", "REAL DEFAULT NULL")
    _ensure_column(conn, "knowledge_library", "anika_reasoning", "TEXT DEFAULT NULL")
    _ensure_column(conn, "knowledge_library", "user_confirmed_purpose", "TEXT DEFAULT NULL")
    _ensure_column(conn, "knowledge_library", "custom_purpose_label", "TEXT DEFAULT NULL")
    _ensure_column(conn, "knowledge_library", "is_custom_purpose", "INTEGER DEFAULT 0")
    # teaching_queue — confirmation-flow columns:
    _ensure_column(conn, "teaching_queue", "anika_proposed_purpose", "TEXT DEFAULT NULL")
    _ensure_column(conn, "teaching_queue", "anika_proposed_confidence", "REAL DEFAULT NULL")
    _ensure_column(conn, "teaching_queue", "anika_reasoning", "TEXT DEFAULT NULL")
    _ensure_column(conn, "teaching_queue", "anika_suggested_sl", "TEXT DEFAULT NULL")
    _ensure_column(conn, "teaching_queue", "anika_suggested_custom", "TEXT DEFAULT NULL")
    _ensure_column(conn, "teaching_queue", "humility_articulation", "TEXT DEFAULT NULL")
    _ensure_column(conn, "teaching_queue", "awaiting_confirmation", "INTEGER DEFAULT 1")

    # Create vec0 virtual tables — depend on sqlite-vec being loaded.
    # memory_vec backs the original `memory` table.
    # knowledge_library_vec backs the new user-taught `knowledge_library` rows —
    # separate so retrieval can filter by table without joining through memory.
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_vec USING vec0(
            memory_id INTEGER PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIM}]
        )
        """
    )
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_library_vec USING vec0(
            library_id INTEGER PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIM}]
        )
        """
    )

    # Seed default system_state keys if absent.
    for key, value in [
        ("kill_switch", "off"),
        ("drafting_paused", "off"),       # new — pauses only the drafting pipeline
        ("last_gmail_history_id", ""),
        ("daily_sent_count", "0"),
        ("daily_sent_date", ""),
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO system_state(key, value) VALUES (?, ?)",
            (key, value),
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
