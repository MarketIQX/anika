"""Global kill switch — stops Anika from drafting or sending.

When ON, the orchestrator short-circuits: no classification, no drafting,
no sending. Incoming emails are still recorded in raw_emails so nothing is
lost. Dashboard and the orchestrator both check this before any work.
"""
from __future__ import annotations

from app.db import execute, fetch_one


def is_on() -> bool:
    row = fetch_one("SELECT value FROM system_state WHERE key='kill_switch'")
    return bool(row and row["value"] == "on")


def set_on() -> None:
    execute(
        """
        INSERT INTO system_state(key, value) VALUES('kill_switch','on')
        ON CONFLICT(key) DO UPDATE SET value='on',
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """
    )


def set_off() -> None:
    execute(
        """
        INSERT INTO system_state(key, value) VALUES('kill_switch','off')
        ON CONFLICT(key) DO UPDATE SET value='off',
          updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """
    )
