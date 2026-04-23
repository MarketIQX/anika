"""Daily send cap — hard limit on how many sends Anika can do per UTC day.

Counter and date are stored in system_state. On a new day (daily_sent_date
!= today), the counter resets to 0 on first read.

Why UTC: avoids DST / timezone weirdness. One day = 24 hours rolling.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.db import execute, fetch_one


def _today_key() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _get_state() -> tuple[int, str]:
    row_count = fetch_one("SELECT value FROM system_state WHERE key='daily_sent_count'")
    row_date = fetch_one("SELECT value FROM system_state WHERE key='daily_sent_date'")
    count = int(row_count["value"]) if row_count and row_count["value"] else 0
    date = (row_date["value"] if row_date else "") or ""
    return count, date


def _set_state(count: int, date: str) -> None:
    execute(
        """
        INSERT INTO system_state(key, value) VALUES('daily_sent_count', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value,
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """,
        (str(count),),
    )
    execute(
        """
        INSERT INTO system_state(key, value) VALUES('daily_sent_date', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value,
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """,
        (date,),
    )


def remaining() -> int:
    """Return how many sends are left today."""
    cap = get_settings().daily_send_cap
    today = _today_key()
    count, date = _get_state()
    if date != today:
        _set_state(0, today)
        return cap
    return max(cap - count, 0)


def try_consume() -> bool:
    """Attempt to reserve a send. Return True if capacity existed (and was consumed)."""
    cap = get_settings().daily_send_cap
    today = _today_key()
    count, date = _get_state()
    if date != today:
        count = 0
        date = today
    if count >= cap:
        _set_state(count, date)
        return False
    _set_state(count + 1, date)
    return True


def status() -> dict[str, int | str]:
    cap = get_settings().daily_send_cap
    count, date = _get_state()
    today = _today_key()
    if date != today:
        count = 0
    return {"cap": cap, "sent_today": count, "remaining": max(cap - count, 0), "date": today}
