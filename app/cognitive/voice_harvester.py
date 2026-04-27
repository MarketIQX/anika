"""Phase 1C-3 — voice example ingestion service.

Single source of truth for creating knowledge_library voice_example rows.
Three pathways feed it; this module makes them produce identical schema
and attribution:

  - 'edit_approval'   — approver.approve() saves the final body of a draft
                        chain after Prakash sir edited then approved it.
  - 'gmail_outbound'  — outbound_harvester saves the partner's Gmail-direct
                        reply (Phase 1C-3 primary use case). Same shape.
  - 'manual_upload'   — /train uploads (placeholder — wired in a future
                        commit). Same shape.

Why one module, not three call sites:
  - Signature stripping must be byte-identical across pathways.
  - knowledge_library row shape (purpose, user_confirmed_purpose,
    harvest_source) must be identical across pathways.
  - reasoning_log attribution differs by pathway but is small and
    deterministic — branched on `source`.

This commit (2a) is pure refactor: the only currently-exercised pathway
is 'edit_approval', and its DB output is byte-identical to what
approver._save_as_voice_example produced before the extraction (modulo
the new harvest_source column, which is the whole reason 1C-3 exists).

Embedding-similarity dedup is added in commit 2b; this commit deliberately
does not include it.
"""
from __future__ import annotations

import logging
from typing import Literal

from app.cognitive import library, reasoning_log
from app.config.firm_identity import strip_signature_block
from app.db import execute as db_execute

logger = logging.getLogger(__name__)


HarvestSource = Literal["edit_approval", "gmail_outbound", "manual_upload"]


# Body must be at least this long AFTER signature stripping. Below this,
# the example is too thin to be useful retrieval signal.
MIN_BODY_CHARS = 50


def harvest_voice_example(
    *,
    sent_body: str,
    service_line: str | None,
    created_by: str,
    source: HarvestSource,
    source_email_id: int | None = None,
    source_draft_id: int | None = None,
) -> int | None:
    """Strip signature, save sent_body to knowledge_library as a voice_example.

    Args:
        sent_body: the body the partner sent (or approved). Signature is
            stripped before save so the example teaches voice only.
        service_line: e.g. 'nri_tax'. None → 'universal' scope.
        created_by: actor identity (user email or synthetic agent name).
        source: pathway tag — written to harvest_source column. Drives
            reasoning_log attribution + reasoning text format.
        source_email_id: raw_emails.id, when known. Logged for audit.
        source_draft_id: drafts.id, when known. Logged for audit.

    Returns:
        library_id on save. None if skipped (body too short after sig strip,
        or library.add_entry returned None due to embedding failure).
    """
    body = strip_signature_block(sent_body or "")
    if len(body) < MIN_BODY_CHARS:
        logger.info(
            "skipping voice_example save (source=%s draft=%s email=%s) — "
            "body too short after sig strip (%d chars)",
            source, source_draft_id, source_email_id, len(body),
        )
        return None

    sl = (service_line or "").strip() or None

    entry_id = library.add_entry(
        kind="example",
        content=body,
        service_line=sl,
        scope="service_line" if sl else "universal",
        source_queue_id=None,
        confidence=1.0,
        created_by=created_by,
    )
    if entry_id is None:
        # add_entry returns None on embedding failure or empty content.
        # Already logged at the source.
        return None

    # Per-source attribution. The mapping is deterministic so the output
    # column shape is the same regardless of caller.
    if source == "edit_approval":
        reasoning_text = (
            f"Auto-saved from approved draft #{source_draft_id} "
            f"(edited then approved)"
        )
        agent_name = "approver"
        decision_label = "auto_voice_example"
    elif source == "gmail_outbound":
        reasoning_text = (
            f"Harvested from partner Gmail-direct reply "
            f"(email #{source_email_id})"
        )
        agent_name = "outbound_harvester"
        decision_label = "harvested_outbound"
    elif source == "manual_upload":
        reasoning_text = f"Manually uploaded by {created_by}"
        agent_name = "train"
        decision_label = "manual_upload"
    else:
        # Defensive — Literal should prevent this, but raise loudly rather
        # than silently miscategorize a row.
        raise ValueError(f"unknown harvest source: {source!r}")

    db_execute(
        """UPDATE knowledge_library SET
              purpose = 'voice_example',
              user_confirmed_purpose = 'voice_example',
              anika_reasoning = ?,
              harvest_source = ?
           WHERE id = ?""",
        (reasoning_text, source, entry_id),
    )

    input_obj: dict = {
        "decision": decision_label,
        "source": source,
        "service_line": sl,
    }
    if source_draft_id is not None:
        input_obj["draft_id"] = source_draft_id
    if source_email_id is not None:
        input_obj["email_id"] = source_email_id

    reasoning_log.log(
        agent_name=agent_name,
        input_obj=input_obj,
        output_obj={"library_id": entry_id},
        draft_id=source_draft_id,
        email_id=source_email_id,
    )
    logger.info(
        "Saved voice_example via %s (library id=%s, source=%s, sl=%s)",
        agent_name, entry_id, source, sl,
    )
    return entry_id
