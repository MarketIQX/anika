"""Approver — handles Prakash sir's decision from the dashboard.

Three paths:
  - approve : insert approvals row; queue the Sender.
  - edit    : insert approvals row with instruction; re-run Drafter to produce
              a new draft. The new draft lands in pending_approval.
  - reject  : insert approvals row; mark the draft rejected. Optionally learn.

The BEFORE UPDATE trigger on `drafts` ensures that an 'approved' approval
row exists before any draft can be marked 'sent'.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents import drafter, sender
from app.agents.schemas import EnricherOutput
from app.cognitive import learning_engine, reasoning_log
from app.db import execute, fetch_one

logger = logging.getLogger(__name__)


def _load_draft(draft_id: int) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT d.*, e.likely_service_line, e.sender_name, e.sender_org, e.sender_country,
               e.urgency, e.routing_partner, e.summary, e.reasoning AS enr_reasoning,
               r.subject AS orig_subject, r.from_email, r.from_name, r.body_plain
          FROM drafts d
          JOIN raw_emails r ON r.id = d.email_id
          LEFT JOIN enrichments e ON e.email_id = d.email_id
         WHERE d.id = ?
        """,
        (draft_id,),
    )
    if not row:
        raise ValueError(f"draft {draft_id} not found")
    return row


def _insert_approval(
    draft_id: int,
    decision: str,
    *,
    edit_instruction: str | None = None,
    decided_by: str = "prakasha",
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> int:
    cur = execute(
        """
        INSERT INTO approvals
          (draft_id, decision, decided_by, edit_instruction, user_agent, ip_address)
        VALUES (?,?,?,?,?,?)
        """,
        (draft_id, decision, decided_by, edit_instruction, user_agent, ip_address),
    )
    return int(cur.lastrowid)


async def approve(
    draft_id: int,
    *,
    decided_by: str = "prakasha",
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Mark the draft approved and fire the Sender after the undo window."""
    row = _load_draft(draft_id)
    if row["sent_status"] not in ("pending_approval",):
        raise ValueError(f"draft {draft_id} has status {row['sent_status']}; cannot approve")

    approval_id = _insert_approval(
        draft_id, "approved",
        decided_by=decided_by, user_agent=user_agent, ip_address=ip_address,
    )
    execute(
        "UPDATE drafts SET sent_status='approved' WHERE id=? AND sent_status='pending_approval'",
        (draft_id,),
    )

    reasoning_log.log(
        agent_name="approver",
        input_obj={"decision": "approved", "draft_id": draft_id, "decided_by": decided_by},
        output_obj={"approval_id": approval_id},
        draft_id=draft_id,
    )
    sent_log_id = await sender.send_approved_draft(draft_id, approval_id)
    return {"approval_id": approval_id, "sent_log_id": sent_log_id}


async def edit(
    draft_id: int,
    edit_instruction: str,
    *,
    decided_by: str = "prakasha",
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> int:
    """Record the edit, re-run the Drafter, and return the new draft id.

    Learning is triggered when the user later approves the revised draft,
    with the edit_delta computed against the approved body (see learning_engine).
    """
    row = _load_draft(draft_id)
    if row["sent_status"] != "pending_approval":
        raise ValueError(f"draft {draft_id} has status {row['sent_status']}; cannot edit")

    approval_id = _insert_approval(
        draft_id, "edited",
        edit_instruction=edit_instruction,
        decided_by=decided_by, user_agent=user_agent, ip_address=ip_address,
    )
    execute(
        "UPDATE drafts SET sent_status='edited' WHERE id=? AND sent_status='pending_approval'",
        (draft_id,),
    )

    # Rebuild the minimal EnricherOutput needed by the Drafter.
    enrichment = EnricherOutput(
        sender_name=row.get("sender_name") or "",
        sender_org=row.get("sender_org") or "",
        sender_country=row.get("sender_country") or "",
        likely_service_line=row.get("likely_service_line") or "other",
        urgency=row.get("urgency") or "warm",
        routing_partner=row.get("routing_partner") or "",
        summary=row.get("summary") or "",
        reasoning=row.get("enr_reasoning") or "",
    )

    new_id = await drafter.draft_reply(
        email_id=row["email_id"],
        from_email=row["from_email"],
        from_name=row["from_name"] or "",
        subject=row["orig_subject"] or "",
        body_plain=row["body_plain"] or "",
        enrichment=enrichment,
        edit_instruction=edit_instruction,
        previous_draft_body=row["body"],
        parent_draft_id=draft_id,
    )

    reasoning_log.log(
        agent_name="approver",
        input_obj={
            "decision": "edited",
            "draft_id": draft_id,
            "edit_instruction": edit_instruction,
        },
        output_obj={"approval_id": approval_id, "new_draft_id": new_id},
        draft_id=draft_id,
    )

    # Learn from the edit pair (original -> revised). We pass the *new* draft's
    # body as the 'after' so the learner sees what Prakash sir effectively
    # asked for.
    new_body_row = fetch_one("SELECT body FROM drafts WHERE id=?", (new_id,))
    new_body = (new_body_row or {}).get("body") or ""
    try:
        learning_engine.on_edit(
            draft_id=draft_id,
            original_body=row["body"],
            edited_body=new_body,
            edit_instruction=edit_instruction,
            approval_id=approval_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("learning_engine.on_edit failed: %s", e)

    return new_id


def reject(
    draft_id: int,
    *,
    note: str | None = None,
    decided_by: str = "prakasha",
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> int:
    """Mark the draft rejected. Returns the approval id."""
    row = _load_draft(draft_id)
    if row["sent_status"] != "pending_approval":
        raise ValueError(f"draft {draft_id} has status {row['sent_status']}; cannot reject")

    approval_id = _insert_approval(
        draft_id, "rejected",
        edit_instruction=note,
        decided_by=decided_by, user_agent=user_agent, ip_address=ip_address,
    )
    execute(
        "UPDATE drafts SET sent_status='rejected' WHERE id=? AND sent_status='pending_approval'",
        (draft_id,),
    )
    reasoning_log.log(
        agent_name="approver",
        input_obj={"decision": "rejected", "draft_id": draft_id, "note": note},
        output_obj={"approval_id": approval_id},
        draft_id=draft_id,
    )
    return approval_id
