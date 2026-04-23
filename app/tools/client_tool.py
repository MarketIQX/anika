"""Client directory lookup — VIP and existing-client detection.

A sender matches an existing client when their email address is present
in the `clients` table. VIP is a boolean column on the same row.

Why a separate tool: Enricher needs this signal to route VIPs to summary-
only mode (no auto-draft) and to let the Drafter use first-name salutations
for established relationships.
"""
from __future__ import annotations

from typing import Any

from app.db import execute, fetch_all, fetch_one


def lookup_client(email: str) -> dict[str, Any] | None:
    """Return the clients row for this email, or None.

    Matching is exact + case-insensitive.
    """
    return fetch_one(
        "SELECT * FROM clients WHERE lower(email) = lower(?) LIMIT 1",
        (email,),
    )


def is_vip(email: str) -> bool:
    """Return True if the sender is flagged VIP in the clients table."""
    row = lookup_client(email)
    return bool(row and row.get("is_vip"))


def list_vips() -> list[dict[str, Any]]:
    return fetch_all(
        "SELECT id, email, name, organisation, notes FROM clients WHERE is_vip=1 ORDER BY name"
    )


def upsert_client(
    email: str,
    name: str | None = None,
    organisation: str | None = None,
    country: str | None = None,
    is_vip_flag: bool = False,
    notes: str | None = None,
) -> int:
    """Insert-or-update a clients row. Returns the client id."""
    existing = lookup_client(email)
    if existing:
        execute(
            """
            UPDATE clients
               SET name=COALESCE(?, name),
                   organisation=COALESCE(?, organisation),
                   country=COALESCE(?, country),
                   is_vip=?,
                   notes=COALESCE(?, notes),
                   updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
             WHERE id=?
            """,
            (name, organisation, country, 1 if is_vip_flag else 0, notes, existing["id"]),
        )
        return int(existing["id"])
    cur = execute(
        """
        INSERT INTO clients(email, name, organisation, country, is_vip, notes)
        VALUES (?,?,?,?,?,?)
        """,
        (email.lower(), name, organisation, country, 1 if is_vip_flag else 0, notes),
    )
    return int(cur.lastrowid)


def set_vip(client_id: int, vip: bool) -> None:
    execute(
        "UPDATE clients SET is_vip=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
        (1 if vip else 0, client_id),
    )


def delete_client(client_id: int) -> None:
    execute("DELETE FROM clients WHERE id=?", (client_id,))
