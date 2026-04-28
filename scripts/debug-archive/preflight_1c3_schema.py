"""Pre-flight verification for Phase 1C-3 schema migration.

Runs init_db() against a COPY of anika.db (never the live DB) and verifies:

  1. raw_emails: outbound_reply_gmail_id + outbound_reply_harvested_at columns added
  2. knowledge_library: harvest_source column added
  3. drafts: sent_status CHECK constraint includes 'rejected_partner_replied_outside'
  4. Row counts unchanged on all three tables
  5. Indexes preserved on drafts (idx_drafts_email, idx_drafts_status)
  6. Triggers preserved on drafts (enforce_approval_before_send, drafts_touch_updated_at)
  7. Functional: inserting a row with sent_status='rejected_partner_replied_outside' SUCCEEDS
  8. Functional: inserting a row with sent_status='garbage' FAILS (CHECK still enforces)
  9. PRAGMA table_info parity vs. a fresh DB built from schema.sql

Reports PASS/FAIL line-by-line, then exits with status 0 (all pass) or 1 (any fail).
The preflight DB file is removed at the end.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).parent
LIVE_DB = REPO / "anika.db"
PREFLIGHT_DB = REPO / "anika.db.preflight-1c-3"

# Import init_db AFTER setting up the path. This module pulls in app.config
# but does not auto-create a connection until init_db() is called.
sys.path.insert(0, str(REPO))
from app.db.connection import init_db, _row_to_dict  # noqa: E402

results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    results.append((ok, msg))
    marker = "PASS" if ok else "FAIL"
    print(f"  [{marker}] {msg}")


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

    print(f"\n=== Pre-flight 1C-3 schema migration ===")
    print(f"Source : {LIVE_DB}  ({LIVE_DB.stat().st_size:,} bytes)")
    print(f"Copy   : {PREFLIGHT_DB}\n")

    # ---- 1. Copy live DB ---------------------------------------------------
    if PREFLIGHT_DB.exists():
        PREFLIGHT_DB.unlink()
    shutil.copy(LIVE_DB, PREFLIGHT_DB)

    # Pre-migration row counts (raw connection — do NOT run init_db yet).
    raw = sqlite3.connect(str(PREFLIGHT_DB))
    raw.row_factory = _row_to_dict
    pre_drafts = raw.execute("SELECT COUNT(*) AS n FROM drafts").fetchone()["n"]
    pre_emails = raw.execute("SELECT COUNT(*) AS n FROM raw_emails").fetchone()["n"]
    pre_kl = raw.execute("SELECT COUNT(*) AS n FROM knowledge_library").fetchone()["n"]
    pre_drafts_idx = list_objects(raw, "index", "drafts")
    pre_drafts_trg = list_objects(raw, "trigger", "drafts")
    raw.close()

    print(f"Pre-state: drafts={pre_drafts}  raw_emails={pre_emails}  knowledge_library={pre_kl}")
    print(f"           drafts indexes={pre_drafts_idx}")
    print(f"           drafts triggers={pre_drafts_trg}\n")

    # ---- 2. Run init_db on the copy ---------------------------------------
    print("Running init_db() against the copy...")
    conn = init_db(PREFLIGHT_DB)
    print("init_db() completed.\n")

    print("Verifying post-migration state:")

    # ---- 3. Column additions ---------------------------------------------
    re_cols = pragma_columns(conn, "raw_emails")
    check("outbound_reply_gmail_id" in re_cols, "raw_emails.outbound_reply_gmail_id added")
    check("outbound_reply_harvested_at" in re_cols, "raw_emails.outbound_reply_harvested_at added")

    kl_cols = pragma_columns(conn, "knowledge_library")
    check("harvest_source" in kl_cols, "knowledge_library.harvest_source added")

    # ---- 4. CHECK constraint expansion ----------------------------------
    drafts_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='drafts'"
    ).fetchone()["sql"]
    check(
        "rejected_partner_replied_outside" in drafts_sql,
        "drafts.sent_status CHECK includes 'rejected_partner_replied_outside'",
    )
    # And the original values must still be there.
    for v in ("pending_approval", "approved", "sending", "sent", "rejected", "edited", "expired"):
        check(v in drafts_sql, f"drafts.sent_status CHECK preserves '{v}'")

    # ---- 5. Row counts unchanged ----------------------------------------
    post_drafts = conn.execute("SELECT COUNT(*) AS n FROM drafts").fetchone()["n"]
    post_emails = conn.execute("SELECT COUNT(*) AS n FROM raw_emails").fetchone()["n"]
    post_kl = conn.execute("SELECT COUNT(*) AS n FROM knowledge_library").fetchone()["n"]
    check(post_drafts == pre_drafts, f"drafts row count unchanged ({pre_drafts} -> {post_drafts})")
    check(post_emails == pre_emails, f"raw_emails row count unchanged ({pre_emails} -> {post_emails})")
    check(post_kl == pre_kl, f"knowledge_library row count unchanged ({pre_kl} -> {post_kl})")

    # ---- 6. Indexes + triggers preserved on drafts ----------------------
    post_drafts_idx = list_objects(conn, "index", "drafts")
    post_drafts_trg = list_objects(conn, "trigger", "drafts")
    for idx in ("idx_drafts_email", "idx_drafts_status"):
        check(idx in post_drafts_idx, f"drafts index {idx} preserved")
    for trg in ("enforce_approval_before_send", "drafts_touch_updated_at"):
        check(trg in post_drafts_trg, f"drafts trigger {trg} preserved")

    # ---- 7. Functional: insert with new sent_status value succeeds ------
    # Pick any existing email_id to satisfy FK; if none, skip.
    eid_row = conn.execute("SELECT id FROM raw_emails LIMIT 1").fetchone()
    if eid_row:
        eid = eid_row["id"]
        try:
            cur = conn.execute(
                """INSERT INTO drafts (email_id, subject, body, sent_status, model)
                   VALUES (?, 'preflight-test', 'preflight-test-body',
                           'rejected_partner_replied_outside', 'preflight')""",
                (eid,),
            )
            new_id = cur.lastrowid
            check(True, "INSERT with sent_status='rejected_partner_replied_outside' accepted")
            conn.execute("DELETE FROM drafts WHERE id=?", (new_id,))
        except sqlite3.IntegrityError as e:
            check(False, f"INSERT with new sent_status REJECTED: {e}")

        # ---- 8. Functional: garbage value still rejected ----------------
        try:
            conn.execute(
                """INSERT INTO drafts (email_id, subject, body, sent_status, model)
                   VALUES (?, 'preflight-test', 'preflight-test-body',
                           'garbage_value', 'preflight')""",
                (eid,),
            )
            check(False, "INSERT with sent_status='garbage_value' was ACCEPTED (CHECK broken)")
        except sqlite3.IntegrityError:
            check(True, "INSERT with sent_status='garbage_value' rejected by CHECK")
    else:
        check(True, "no raw_emails rows — skipping functional insert tests")

    # ---- 9. PRAGMA parity vs. fresh DB built from schema.sql ------------
    print()
    print("PRAGMA parity check vs. fresh DB built from schema.sql:")
    fresh_path = Path(tempfile.mkdtemp()) / "fresh.db"
    fresh_conn = init_db(fresh_path)
    for tbl in ("raw_emails", "drafts", "knowledge_library"):
        live_cols = pragma_columns(conn, tbl)
        fresh_cols = pragma_columns(fresh_conn, tbl)
        check(
            live_cols == fresh_cols,
            f"{tbl} column list matches fresh DB "
            f"({'identical' if live_cols == fresh_cols else f'live={live_cols} fresh={fresh_cols}'})",
        )
    fresh_conn.close()
    try:
        fresh_path.unlink()
    except OSError:
        pass

    conn.close()

    # ---- Cleanup --------------------------------------------------------
    if PREFLIGHT_DB.exists():
        PREFLIGHT_DB.unlink()
    print(f"\nPreflight DB removed: {PREFLIGHT_DB}")

    # ---- Summary --------------------------------------------------------
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
