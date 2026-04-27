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

Embedding-similarity dedup (commit 2b): before saving, the harvester
embeds the candidate body and queries knowledge_library_vec for the
nearest active voice_example in the same scope. If the L2 distance is
below DEDUP_DISTANCE_THRESHOLD, the existing entry's library_id is
returned and no new row is created. Prevents bloat when the harvester
finds essentially-the-same partner reply across multiple polls, or when
the partner approves a near-identical draft body twice.
"""
from __future__ import annotations

import logging
import struct
from typing import Literal

from app.cognitive import library, reasoning_log
from app.config.firm_identity import strip_signature_block
from app.db import EMBEDDING_DIM, execute as db_execute, fetch_all, fetch_one
from app.tools import memory_tool

logger = logging.getLogger(__name__)


HarvestSource = Literal["edit_approval", "gmail_outbound", "manual_upload"]


# Body must be at least this long AFTER signature stripping. Below this,
# the example is too thin to be useful retrieval signal.
MIN_BODY_CHARS = 50


# L2 distance threshold below which two voice_examples are treated as
# duplicates. OpenAI text-embedding-3-small returns unit-normalized
# vectors, so for unit vectors L2 = sqrt(2 - 2·cos(θ)). Reference points:
#     cosine 1.00  →  L2 = 0.000  (identical text)
#     cosine 0.99  →  L2 ≈ 0.141
#     cosine 0.97  →  L2 ≈ 0.245
#     cosine 0.95  →  L2 ≈ 0.316
#     cosine 0.90  →  L2 ≈ 0.447
# 0.30 corresponds to ~cos 0.955 — "essentially the same content, perhaps
# with whitespace or single-word differences". Tuned conservative on
# purpose: only very-near duplicates are flagged, and the threshold is
# easy to relax once production data shows real duplicate-rate.
DEDUP_DISTANCE_THRESHOLD = 0.30


def _pack_vector(vec: list[float]) -> bytes:
    """Pack a vector for sqlite-vec MATCH lookups (little-endian float32)."""
    if len(vec) != EMBEDDING_DIM:
        raise ValueError(f"expected {EMBEDDING_DIM}-dim vector, got {len(vec)}")
    return struct.pack(f"{EMBEDDING_DIM}f", *vec)


def _find_duplicate_voice_example(
    content: str,
    service_line: str | None,
) -> int | None:
    """Return the library_id of an active near-duplicate voice_example, or None.

    Service-line scope rules:
      - service_line is None → match against universal-scope examples only.
      - service_line is set  → match against same-service-line OR universal.
    Same content under DIFFERENT service lines is NOT a duplicate; voice
    can be reused across lines but partner edits in different lines are
    independent signal.

    Soft-deleted (is_active=0) entries never match — we don't want a
    previously-removed example to silently block a fresh save.

    Cheap path: if no active voice_examples exist at all, skip the embed
    call entirely.

    Best-effort: any embed/query failure logs a warning and returns None
    (i.e. proceed with save). Dedup is a quality-of-life optimization, not
    a correctness invariant.
    """
    has_any = fetch_one(
        "SELECT 1 AS x FROM knowledge_library "
        "WHERE is_active = 1 AND purpose = 'voice_example' LIMIT 1"
    )
    if not has_any:
        return None

    try:
        qvec = memory_tool.embed(content)
    except Exception as e:  # noqa: BLE001
        logger.warning("dedup embed failed, skipping dedup check: %s", e)
        return None
    if not qvec:
        return None

    try:
        packed = _pack_vector(qvec)
    except ValueError as e:
        logger.warning("dedup pack failed, skipping dedup check: %s", e)
        return None

    # K=10 over-fetch then filter by scope. If the closest 10 don't include
    # a same-scope hit below threshold, a more distant one is not a duplicate.
    rows = fetch_all(
        """
        SELECT v.library_id AS id, v.distance AS distance,
               k.service_line AS service_line, k.scope AS scope
          FROM knowledge_library_vec v
          JOIN knowledge_library k ON k.id = v.library_id
         WHERE v.embedding MATCH ? AND k = ?
           AND k.is_active = 1
           AND k.purpose = 'voice_example'
         ORDER BY v.distance
        """,
        (packed, 10),
    )
    for r in rows:
        if r["distance"] >= DEDUP_DISTANCE_THRESHOLD:
            # Rows are sorted by distance ASC — once we cross threshold,
            # nothing further down is a duplicate either.
            break
        row_sl = r.get("service_line")
        row_scope = r.get("scope")
        if service_line is None:
            if row_scope == "universal":
                return int(r["id"])
        else:
            if row_sl == service_line or row_scope == "universal":
                return int(r["id"])
    return None


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

    # Dedup: if a near-duplicate active voice_example already exists in
    # the same scope, return its id and skip the save. Caller treats this
    # as "content represented in the library" — same return contract as
    # a fresh save. The existing row's attribution is preserved.
    duplicate_id = _find_duplicate_voice_example(body, sl)
    if duplicate_id is not None:
        logger.info(
            "voice_example dedup hit (source=%s sl=%s) — matched library id=%s, skipping save",
            source, sl, duplicate_id,
        )
        return duplicate_id

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
