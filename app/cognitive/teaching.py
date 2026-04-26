"""Teaching-queue orchestration — glue between upload routes and the Learner.

Flow:
  enqueue_text(...) or enqueue_file(...) creates a teaching_queue row (status=pending).
  finalize_queue(id) runs:
    1. Extract text (if file)
    2. Run the Learner to produce units + clarifications
    3. Persist clarifications; persist units that aren't blocked by clarifications
    4. Update queue status

answer_clarification(...) records the reply and, if all clarifications are answered,
promotes the queued unit to knowledge_library.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.agents import teaching_learner
from app.agents.teaching_learner import (
    LearnerOutput,
    LearnerUnit,
    cap_clarifications,
    detect_pii_in_unit,
)
from app.cognitive import library
from app.db import execute, fetch_all, fetch_one

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"


def _ensure_uploads_dir() -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def enqueue_text(*, raw_content: str, created_by: str) -> int:
    cur = execute(
        """
        INSERT INTO teaching_queue
          (raw_content, source_type, created_by_user, status)
        VALUES (?, 'text', ?, 'pending')
        """,
        (raw_content, created_by),
    )
    return int(cur.lastrowid)


def enqueue_file(
    *,
    raw_content: str,
    file_mime: str | None,
    original_filename: str,
    stored_path: str,
    created_by: str,
) -> int:
    cur = execute(
        """
        INSERT INTO teaching_queue
          (raw_content, source_type, file_mime, original_filename,
           stored_path, created_by_user, status)
        VALUES (?, 'file', ?, ?, ?, ?, 'pending')
        """,
        (raw_content, file_mime, original_filename, stored_path, created_by),
    )
    return int(cur.lastrowid)


async def finalize_queue(queue_id: int) -> dict[str, Any]:
    """Run the Learner on a pending queue row and persist its output.

    Returns a summary: {units_added, clarifications_pending, clarifications_deferred,
                         status}.
    """
    row = fetch_one("SELECT * FROM teaching_queue WHERE id=?", (queue_id,))
    if not row:
        raise ValueError(f"teaching_queue {queue_id} not found")
    if row["status"] not in ("pending",):
        return {"status": row["status"], "note": "already processed"}

    execute("UPDATE teaching_queue SET status='processing' WHERE id=?", (queue_id,))

    source_hint = (
        f"{row['source_type']} upload"
        + (f" ({row['original_filename']})" if row.get("original_filename") else "")
    )
    try:
        # Call via the module so tests monkeypatching teaching_learner.extract work.
        output: LearnerOutput = await teaching_learner.extract(
            row["raw_content"], source_hint=source_hint,
        )
    except Exception as e:  # noqa: BLE001
        execute(
            "UPDATE teaching_queue SET status='failed', error_text=?, "
            "processed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (str(e)[:500], queue_id),
        )
        logger.exception("learner failed on queue %s: %s", queue_id, e)
        return {"status": "failed", "error": str(e)}

    surface, defer = cap_clarifications(output)

    # If there are any clarifications on a unit, defer ONLY that unit. Units
    # without clarifications land straight in knowledge_library.
    clarified_indices = {c.target_unit_index for c in output.clarifications}

    units_added = 0
    for i, unit in enumerate(output.units):
        if i in clarified_indices:
            continue  # wait for user's answer before storing
        _store_unit(unit, queue_id=queue_id, created_by=row["created_by_user"])
        units_added += 1

    # Persist clarifications (both surface-now and deferred; deferred marked
    # with a distinct but the UI can fold them).
    for c in surface:
        _store_clarification(queue_id, c, priority="surface",
                             unit_content=output.units[c.target_unit_index].content
                             if 0 <= c.target_unit_index < len(output.units) else "")
    for c in defer:
        _store_clarification(queue_id, c, priority="defer",
                             unit_content=output.units[c.target_unit_index].content
                             if 0 <= c.target_unit_index < len(output.units) else "")

    # Flag PII on any stored unit — this is a soft review hint, stored as a
    # clarification so the user sees it in the pending queue.
    for i, unit in enumerate(output.units):
        if i in clarified_indices:
            continue
        pii = detect_pii_in_unit(unit.content)
        if pii:
            _store_clarification(
                queue_id,
                _pii_clarification(unit, i, pii),
                priority="surface",
                unit_content=unit.content,
            )

    new_status = "needs_clarification" if output.clarifications or units_added == 0 else "approved"
    execute(
        "UPDATE teaching_queue SET status=?, processed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
        "WHERE id=?",
        (new_status, queue_id),
    )
    return {
        "status": new_status,
        "units_added": units_added,
        "clarifications_pending": len(surface),
        "clarifications_deferred": len(defer),
    }


def _pii_clarification(unit: LearnerUnit, index: int, kinds: list[str]):
    """Synthesize a clarification question for a PII-flagged unit."""
    from app.agents.teaching_learner import LearnerClarification

    return LearnerClarification(
        question_text=(
            f"This unit appears to contain PII ({', '.join(kinds)}). "
            "Keep as-is, redact before storing, or reject entirely?"
        ),
        options=["Keep as-is", "Redact and store", "Reject this unit"],
        target_unit_index=index,
    )


def _store_unit(unit: LearnerUnit, *, queue_id: int, created_by: str) -> int | None:
    scope = unit.scope
    service_line = unit.service_line or None
    if scope == "service_line" and not service_line:
        # Defensive — don't let bad LLM output write an inconsistent row.
        scope = "universal"
    if scope == "universal":
        service_line = None
    return library.add_entry(
        kind=unit.kind,
        content=unit.content,
        service_line=service_line,
        scope=scope,
        source_queue_id=queue_id,
        confidence=unit.confidence,
        created_by=created_by,
    )


def _store_clarification(queue_id: int, c, *, priority: str, unit_content: str) -> int:
    cur = execute(
        """
        INSERT INTO clarifications
          (queue_id, question_text, options_json, target_unit_index, unit_preview, status)
        VALUES (?,?,?,?,?, 'pending')
        """,
        (
            queue_id,
            c.question_text,
            json.dumps(c.options, ensure_ascii=False),
            c.target_unit_index,
            unit_content[:500],
        ),
    )
    return int(cur.lastrowid)


# --------------------------------------------------------------------------
# Clarification answering
# --------------------------------------------------------------------------


async def answer_clarification(
    clarification_id: int, *, answer: str, answered_by: str,
) -> dict[str, Any]:
    """Record the user's answer.

    The simple interpretation: the answer becomes the decision on the
    paired unit. For PII-style clarifications ("Keep as-is" / "Redact and
    store" / "Reject"), we apply the action verbatim. For service-line /
    scope clarifications the answer is appended as context to the unit's
    content before storing.
    """
    row = fetch_one("SELECT * FROM clarifications WHERE id=?", (clarification_id,))
    if not row:
        raise ValueError("clarification not found")
    if row["status"] != "pending":
        return {"status": row["status"], "note": "already answered"}

    execute(
        """
        UPDATE clarifications
           SET answer=?, status='answered',
               answered_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE id=?
        """,
        (answer, clarification_id),
    )

    # Re-run learner finalization ONLY for the target unit — simplest path is
    # to re-parse the unit_preview + user's answer as a fresh micro-upload.
    # For Phase 1A we take the pragmatic route: if the answer looks like
    # "Reject this unit", we just mark handled and don't write. Otherwise
    # we store the unit content as a fact/rule with the answer appended as
    # context.
    if "reject" in answer.lower():
        return {"status": "answered", "action": "rejected"}

    unit_preview = (row.get("unit_preview") or "").strip()
    if not unit_preview:
        # Fallback: use the queue's raw_content when Learner didn't
        # persist a unit_preview snapshot.
        queue_row = fetch_one("SELECT raw_content FROM teaching_queue WHERE id=?", (row["queue_id"],))
        unit_preview = (queue_row["raw_content"] if queue_row else "").strip()
    if not unit_preview:
        return {"status": "answered", "action": "no-op-empty-content"}

    # Derive scope + service line from the answer when possible.
    answer_lc = answer.lower()
    service_line = None
    scope = "universal"
    for slug in ("nri_tax", "foreign_subsidiary", "transfer_pricing",
                 "virtual_cfo", "gst_indirect", "secretarial_roc", "audit"):
        if slug in answer_lc:
            service_line = slug
            scope = "service_line"
            break

    # Default kind = 'rule' unless content looks like a whole email.
    kind = "example" if len(unit_preview) > 400 and "Dear" in unit_preview else "rule"

    library.add_entry(
        kind=kind,
        content=unit_preview,
        service_line=service_line,
        scope=scope,
        source_queue_id=row["queue_id"],
        confidence=0.9,
        created_by=answered_by,
    )

    # If all clarifications on this queue are answered, flip its status.
    remaining = fetch_one(
        "SELECT COUNT(*) n FROM clarifications WHERE queue_id=? AND status='pending'",
        (row["queue_id"],),
    )
    if remaining and int(remaining["n"]) == 0:
        execute(
            "UPDATE teaching_queue SET status='approved' WHERE id=?",
            (row["queue_id"],),
        )

    return {"status": "answered", "action": "stored", "kind": kind, "scope": scope}


# --------------------------------------------------------------------------
# Read helpers for the UI
# --------------------------------------------------------------------------


def pending_clarifications() -> list[dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT c.*, q.source_type, q.original_filename
          FROM clarifications c
          LEFT JOIN teaching_queue q ON q.id = c.queue_id
         WHERE c.status = 'pending'
         ORDER BY c.asked_at DESC
        """
    )
    # Decode options_json for the template.
    for r in rows:
        try:
            r["options"] = json.loads(r.get("options_json") or "[]")
        except Exception:  # noqa: BLE001
            r["options"] = []
    return rows


def recent_queue(limit: int = 20) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, source_type, original_filename, status, created_at, processed_at
          FROM teaching_queue
         ORDER BY id DESC
         LIMIT ?
        """,
        (limit,),
    )


async def finalize_with_purpose(
    queue_id: int,
    *,
    confirmed_purpose: str,
    custom_label: str | None = None,
    service_line: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Finalize a queue row using the user's confirmed purpose.

    Unlike finalize_queue (which runs the Learner to extract multiple units),
    this function is for the Phase 1B flow where Anika proposed a purpose
    and the user confirmed/corrected it. The whole queue content becomes
    ONE library entry with the confirmed purpose.
    """
    row = fetch_one("SELECT * FROM teaching_queue WHERE id=?", (queue_id,))
    if not row:
        raise ValueError(f"teaching_queue {queue_id} not found")

    from app.cognitive.library import add_entry

    # Determine kind based on purpose (purposes map to kinds for legacy compatibility)
    kind_map = {
        "voice_example": "example",
        "classifier_example": "example",
        "document_type": "fact",
        "question_template": "rule",
        "workflow_rule": "rule",
        "firm_fact": "fact",
        "firm_policy": "rule",
        "reference_material": "fact",
    }
    kind = kind_map.get(confirmed_purpose, "fact")

    scope = "service_line" if service_line else "universal"
    is_custom = 1 if custom_label else 0

    # Map from queue content and confirmed purpose → library entry
    entry_id = add_entry(
        kind=kind,
        content=row["raw_content"],
        service_line=service_line,
        scope=scope,
        source_queue_id=queue_id,
        confidence=row.get("anika_proposed_confidence") or 0.9,
        created_by=created_by or row["created_by_user"],
    )

    # Now update the extra classification columns we added in Phase 1B
    execute(
        """UPDATE knowledge_library SET
              purpose = ?,
              anika_proposed_purpose = ?,
              anika_proposed_confidence = ?,
              anika_reasoning = ?,
              user_confirmed_purpose = ?,
              custom_purpose_label = ?,
              is_custom_purpose = ?
           WHERE id = ?""",
        (
            confirmed_purpose,
            row.get("anika_proposed_purpose"),
            row.get("anika_proposed_confidence"),
            row.get("anika_reasoning"),
            confirmed_purpose,
            custom_label,
            is_custom,
            entry_id,
        ),
    )

    # Mark queue as approved
    execute(
        "UPDATE teaching_queue SET status='approved', "
        "processed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
        (queue_id,),
    )

    return {
        "status": "approved",
        "library_id": entry_id,
        "purpose": confirmed_purpose,
    }
