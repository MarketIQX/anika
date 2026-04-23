"""Audit trail for logins, approvals, and settings changes.

Append-only at the DB layer (triggers block UPDATE and DELETE). Every caller
that mutates state or authenticates should leave a row here.
"""
from __future__ import annotations

from typing import Any

from app.db import execute, fetch_all

# Canonical action names — any string works, but keeping these grouped helps
# the Admin audit page stay tidy.
ACTIONS = {
    "login_success",
    "login_failure",
    "logout",
    "draft_approve",
    "draft_edit",
    "draft_reject",
    "kill_switch_on",
    "kill_switch_off",
    "client_add",
    "client_update_vip",
    "client_delete",
    "gmail_oauth_start",
    "gmail_oauth_complete",
    "memory_backfill",
    "poll_now",
    "password_change",
    "password_changed",   # self-service change from /account
    "user_create",
}


def log(
    action: str,
    *,
    user_email: str | None = None,
    target: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> int:
    """Insert an access_log row. Returns the row id.

    We don't validate `action` against ACTIONS — new event types can land
    naturally; the set above is just the documented catalog.
    """
    cur = execute(
        """
        INSERT INTO access_log(user_email, action, target, ip_address, user_agent)
        VALUES (?,?,?,?,?)
        """,
        (user_email, action, target, ip_address, user_agent),
    )
    return int(cur.lastrowid)


def recent(limit: int = 200) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, user_email, action, target, ip_address, user_agent, created_at
          FROM access_log
         ORDER BY id DESC
         LIMIT ?
        """,
        (limit,),
    )
