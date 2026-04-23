"""Memory Core — high-level API over the memory_tool.

This layer is what agents see. memory_tool deals with embeddings + sqlite-vec;
this module adds "retrieve few-shot examples for the drafter" and "harvest
an approved draft into memory after a send" conveniences.
"""
from __future__ import annotations

import logging
from typing import Any

from app.db import fetch_one
from app.tools import memory_tool

logger = logging.getLogger(__name__)


def retrieve_few_shot(
    enquiry_text: str,
    service_line: str | None = None,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    """Return a list of exemplar memories to feed the Drafter.

    We prefer kind='approved_draft' (actual sends Prakash sir approved), then
    fall back to kind='exemplar' (seeded few-shot templates). Ordering by
    distance is already handled in memory_tool.
    """
    results = memory_tool.semantic_search(
        query=enquiry_text,
        top_k=top_k,
        service_line=service_line,
        kinds=["approved_draft", "exemplar"],
    )
    return results


def retrieve_firm_snippets(
    enquiry_text: str, top_k: int = 3
) -> list[dict[str, Any]]:
    """Return firm_snippet memories relevant to the enquiry.

    Used by the Enricher to surface positioning/track-record facts the
    Drafter can cite naturally.
    """
    return memory_tool.semantic_search(
        query=enquiry_text,
        top_k=top_k,
        kinds=["firm_snippet"],
    )


def harvest_approved_draft(draft_id: int) -> int | None:
    """After a successful send, store the draft as an approved_draft memory.

    Idempotent: if we've already harvested this draft, we skip.
    """
    row = fetch_one(
        """
        SELECT d.id, d.email_id, d.subject, d.body,
               e.likely_service_line AS service_line,
               m.id AS existing_memory_id
          FROM drafts d
          LEFT JOIN enrichments e ON e.email_id = d.email_id
          LEFT JOIN memory m ON m.source_draft_id = d.id AND m.kind = 'approved_draft'
         WHERE d.id = ?
        """,
        (draft_id,),
    )
    if not row:
        return None
    if row.get("existing_memory_id"):
        return int(row["existing_memory_id"])

    return memory_tool.store_memory(
        kind="approved_draft",
        service_line=row.get("service_line"),
        subject=row.get("subject"),
        content=row.get("body") or "",
        source_email_id=row.get("email_id"),
        source_draft_id=draft_id,
        tags=[row.get("service_line")] if row.get("service_line") else [],
    )


def count_memories_by_kind() -> dict[str, int]:
    """Return counts keyed by kind — used by dashboard analytics."""
    from app.db import fetch_all

    rows = fetch_all("SELECT kind, COUNT(*) AS n FROM memory GROUP BY kind")
    return {r["kind"]: int(r["n"]) for r in rows}
