"""Pre-flight verification for Phase 1C-3 fix schema migration.

Single ADD COLUMN: raw_emails.outbound_last_scanned_at TEXT DEFAULT NULL.
Runs init_db() against a COPY of anika.db (never the live DB) and verifies:

  1. raw_emails.outbound_last_scanned_at column added
  2. Row count unchanged (single-table parity)
  3. Existing harvester-related columns still present
  4. Indexes + triggers on raw_emails preserved
  5. PRAGMA column-list parity vs. a fresh DB built from schema.sql
  6. Functional: a backfilled NULL value for the new column is read back as None
  7. Functional: writing a timestamp into the new column round-trips correctly

Reports PASS/FAIL and exits 0 (all pass) or 1 (any fail). Preflight DB
file is removed at the end.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).parent
LIVE_DB = REPO / "anika.db"
PREFLIGHT_DB = REPO / "anika.db.preflight-1c-3-fix"

sys.path.insert(0, str(REPO))
from app.db.connection import init_db, _row_to_dict  # noqa: E402

results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    results.append((ok, msg))
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def pragma_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def list_objects(conn: sqlite3.Connection, kind: str, tbl: str) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type=? AND tbl_name=? ORDER BY name",
        (kind, tbl),
    ).fetchall()
    return [r["name"] for r in rows]


def main() -> int:
    if not LIVE_DB.exists():
        print(f"ERROR: live DB not found at {LIVE_DB}")
        return 2

    print("\n=== Pre-flight 1C-3 fix schema migration ===")
    print(f"Source : {LIVE_DB}  ({LIVE_DB.stat().st_size:,} bytes)")
    print(f"Copy   : {PREFLIGHT_DB}\n")

    if PREFLIGHT_DB.exists():
        PREFLIGHT_DB.unlink()
    shutil.copy(LIVE_DB, PREFLIGHT_DB)

    # Pre-state on the copy (raw read, no init_db yet).
    raw = sqlite3.connect(str(PREFLIGHT_DB))
    raw.row_factory = _row_to_dict
    pre_emails = raw.execute("SELECT COUNT(*) AS n FROM raw_emails").fetchone()["n"]
    pre_cols = [r["name"] for r in raw.execute("PRAGMA table_info(raw_emails)")]
    pre_indexes = list_objects(raw, "index", "raw_emails")
    pre_triggers = list_objects(raw, "trigger", "raw_emails")
    raw.close()

    print(f"Pre-state: raw_emails={pre_emails} rows, {len(pre_cols)} columns")
    print(f"           indexes={pre_indexes}")
    print(f"           triggers={pre_triggers}\n")

    print("Running init_db() against the copy...")
    conn = init_db(PREFLIGHT_DB)
    print("init_db() completed.\n")

    print("Verifying post-migration state:")

    # ---- 1. New column added --------------------------------------------
    post_cols = pragma_columns(conn, "raw_emails")
    check(
        "outbound_last_scanned_at" in post_cols,
        "raw_emails.outbound_last_scanned_at added",
    )

    # ---- 2. Row count unchanged ----------------------------------------
    post_emails = conn.execute("SELECT COUNT(*) AS n FROM raw_emails").fetchone()["n"]
    check(
        post_emails == pre_emails,
        f"raw_emails row count unchanged ({pre_emails} -> {post_emails})",
    )

    # ---- 3. Existing harvester columns still present -------------------
    for col in ("outbound_reply_gmail_id", "outbound_reply_harvested_at",
                "is_web_form", "gmail_thread_id", "received_at"):
        check(col in post_cols, f"raw_emails.{col} preserved")

    # ---- 4. Indexes + triggers preserved -------------------------------
    post_indexes = list_objects(conn, "index", "raw_emails")
    post_triggers = list_objects(conn, "trigger", "raw_emails")
    for idx in pre_indexes:
        check(idx in post_indexes, f"raw_emails index {idx} preserved")
    for trg in pre_triggers:
        check(trg in post_triggers, f"raw_emails trigger {trg} preserved")

    # ---- 5. PRAGMA parity vs. fresh DB ---------------------------------
    print()
    print("PRAGMA parity check vs. fresh DB built from schema.sql:")
    fresh_path = Path(tempfile.mkdtemp()) / "fresh.db"
    fresh_conn = init_db(fresh_path)
    fresh_cols = pragma_columns(fresh_conn, "raw_emails")
    check(
        post_cols == fresh_cols,
        f"raw_emails column list matches fresh DB "
        f"({'identical' if post_cols == fresh_cols else f'live={post_cols} fresh={fresh_cols}'})",
    )
    fresh_conn.close()
    try:
        fresh_path.unlink()
    except OSError:
        pass

    # ---- 6. Backfill is NULL on existing rows --------------------------
    null_count = conn.execute(
        "SELECT COUNT(*) AS n FROM raw_emails WHERE outbound_last_scanned_at IS NULL"
    ).fetchone()["n"]
    check(
        null_count == post_emails,
        f"all {post_emails} existing rows have NULL outbound_last_scanned_at",
    )

    # ---- 7. Write/read round-trip on the new column --------------------
    eid_row = conn.execute("SELECT id FROM raw_emails LIMIT 1").fetchone()
    if eid_row:
        eid = eid_row["id"]
        ts = "2026-04-27T12:34:56.789Z"
        conn.execute(
            "UPDATE raw_emails SET outbound_last_scanned_at=? WHERE id=?",
            (ts, eid),
        )
        rb = conn.execute(
            "SELECT outbound_last_scanned_at FROM raw_emails WHERE id=?",
            (eid,),
        ).fetchone()["outbound_last_scanned_at"]
        check(rb == ts, "write/read round-trip on outbound_last_scanned_at works")
        # Reset so the column is NULL again — preflight should leave the
        # copy in a state matching the live DB exactly (we'll throw the copy
        # away anyway, but cleanliness matters if someone inspects it).
        conn.execute(
            "UPDATE raw_emails SET outbound_last_scanned_at=NULL WHERE id=?",
            (eid,),
        )
    else:
        check(True, "no raw_emails rows — skipping write/read round-trip")

    conn.close()

    if PREFLIGHT_DB.exists():
        PREFLIGHT_DB.unlink()
    print(f"\nPreflight DB removed: {PREFLIGHT_DB}")

    failed = [m for ok, m in results if not ok]
    total = len(results)
    passed = total - len(failed)
    print(f"\n=== {passed}/{total} checks passed ===")
    if failed:
        print("FAILURES:")
        for m in failed:
            print(f"  - {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
