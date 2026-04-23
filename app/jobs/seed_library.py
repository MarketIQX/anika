"""First-boot seed for the knowledge_library.

If the library is empty AND we have an approved reply to Chandrika in
sent_log (from the production data already on the laptop), migrate it as
the first voice example. This gives the Drafter a real voice sample to
mirror on day one.

Idempotent: runs only when knowledge_library is empty. Safe to call on
every boot.
"""
from __future__ import annotations

import logging

from app.cognitive import library
from app.db import fetch_all, fetch_one

logger = logging.getLogger(__name__)


def maybe_seed_from_sent_log() -> int | None:
    """Return the library id if we seeded, else None."""
    existing = fetch_one("SELECT COUNT(*) n FROM knowledge_library")
    if not existing or int(existing["n"]) > 0:
        return None

    # Look for a Chandrika reply in sent_log — any approved reply where
    # the recipient address contains "chandrika" counts.
    row = fetch_one(
        """
        SELECT sl.body, sl.subject, sl.to_email, d.email_id
          FROM sent_log sl
          JOIN drafts d ON d.id = sl.draft_id
         WHERE lower(sl.to_email) LIKE '%chandrika%'
         ORDER BY sl.sent_at DESC
         LIMIT 1
        """
    )
    if not row:
        return None

    lid = library.add_entry(
        kind="example",
        content=row["body"],
        service_line="nri_tax",
        scope="service_line",
        confidence=1.0,
        created_by="migration",
    )
    if lid:
        logger.info(
            "Seeded knowledge_library with first example from sent_log (Chandrika reply, lid=%s)",
            lid,
        )
    return lid
