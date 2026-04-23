"""Drafting-paused flag — finer-grained than kill_switch.

Difference from kill_switch:
  - kill_switch.is_on() → orchestrator short-circuits BEFORE the classifier;
    no classifications or enrichments run. Use for an emergency halt.
  - drafting_paused.is_on() → orchestrator still ingests/classifies/enriches
    but DOES NOT call the Drafter. Use while actively teaching Anika to
    avoid producing drafts from a prompt you're in the middle of revising.

If either is on, no draft is produced.
"""
from __future__ import annotations

from app.db import execute, fetch_one


def is_on() -> bool:
    row = fetch_one("SELECT value FROM system_state WHERE key='drafting_paused'")
    return bool(row and row["value"] == "on")


def set_on() -> None:
    execute(
        """
        INSERT INTO system_state(key, value) VALUES('drafting_paused','on')
        ON CONFLICT(key) DO UPDATE SET value='on',
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """
    )


def set_off() -> None:
    execute(
        """
        INSERT INTO system_state(key, value) VALUES('drafting_paused','off')
        ON CONFLICT(key) DO UPDATE SET value='off',
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """
    )
