"""The critical test: the DB trigger MUST block a forged send.

This is Anika's hardest guarantee — no email can be marked 'sent' without
a matching approvals row. If this test ever fails, the architecture itself
is broken.
"""
from __future__ import annotations

import sqlite3

import pytest

from app.db import execute, fetch_one


def _seed_email_and_draft() -> tuple[int, int]:
    cur = execute(
        "INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email, to_email, received_at) "
        "VALUES('m1','t1','x@y.com','prakasha@balakrishnaandco.com','2026-04-22T00:00:00Z')"
    )
    email_id = int(cur.lastrowid)
    cur = execute(
        "INSERT INTO drafts(email_id, subject, body, model) VALUES(?,?,?,?)",
        (email_id, "Re: x", "body", "gpt-4o"),
    )
    draft_id = int(cur.lastrowid)
    return email_id, draft_id


def test_forged_send_without_approval_aborts():
    """Direct UPDATE drafts SET sent_status='sent' must be aborted."""
    _, draft_id = _seed_email_and_draft()

    with pytest.raises(sqlite3.IntegrityError) as ei:
        execute("UPDATE drafts SET sent_status='sent' WHERE id=?", (draft_id,))
    assert "Cannot mark as sent without approval row" in str(ei.value)

    # Confirm draft is still at pending_approval.
    row = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    assert row["sent_status"] == "pending_approval"


def test_approved_row_allows_send():
    """When a decision='approved' row exists, the transition to 'sent' succeeds."""
    _, draft_id = _seed_email_and_draft()
    execute(
        "INSERT INTO approvals(draft_id, decision, decided_by) VALUES(?,?,?)",
        (draft_id, "approved", "prakasha"),
    )
    # Path: pending_approval -> approved -> sent
    execute(
        "UPDATE drafts SET sent_status='approved' WHERE id=?", (draft_id,)
    )
    execute("UPDATE drafts SET sent_status='sent' WHERE id=?", (draft_id,))
    row = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    assert row["sent_status"] == "sent"


def test_rejected_approval_does_not_permit_send():
    """An approvals row with decision='rejected' does NOT unlock send."""
    _, draft_id = _seed_email_and_draft()
    execute(
        "INSERT INTO approvals(draft_id, decision, decided_by) VALUES(?,?,?)",
        (draft_id, "rejected", "prakasha"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        execute("UPDATE drafts SET sent_status='sent' WHERE id=?", (draft_id,))


def test_sent_log_is_append_only():
    """Updates and deletes on sent_log must abort."""
    email_id, draft_id = _seed_email_and_draft()
    execute(
        "INSERT INTO approvals(draft_id, decision, decided_by) VALUES(?,?,?)",
        (draft_id, "approved", "prakasha"),
    )
    cur = execute(
        """
        INSERT INTO sent_log
          (draft_id, email_id, approval_id, to_email, subject, body)
        VALUES(?,?,?,?,?,?)
        """,
        (draft_id, email_id, 1, "x@y.com", "subj", "body"),
    )
    sl = int(cur.lastrowid)
    with pytest.raises(sqlite3.IntegrityError):
        execute("UPDATE sent_log SET subject='tampered' WHERE id=?", (sl,))
    with pytest.raises(sqlite3.IntegrityError):
        execute("DELETE FROM sent_log WHERE id=?", (sl,))


def test_reasoning_log_is_append_only():
    execute(
        """
        INSERT INTO reasoning_log(agent_name, input_json, status) VALUES('x','{}','ok')
        """
    )
    row = fetch_one("SELECT id FROM reasoning_log ORDER BY id DESC LIMIT 1")
    rid = int(row["id"])
    with pytest.raises(sqlite3.IntegrityError):
        execute("UPDATE reasoning_log SET reasoning_text='x' WHERE id=?", (rid,))
    with pytest.raises(sqlite3.IntegrityError):
        execute("DELETE FROM reasoning_log WHERE id=?", (rid,))
