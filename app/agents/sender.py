"""Sender — executes the approved Gmail send.

Hard safety rails:
  1. Kill switch must be off.
  2. Daily cap must have capacity.
  3. Draft must currently be 'approved' (i.e. an approvals row with
     decision='approved' exists).
  4. Undo window delay between approval and send (default 10s).
  5. The BEFORE UPDATE trigger on drafts is the last line of defense —
     if any of the above were bypassed in code, the trigger would abort.
"""
from __future__ import annotations

import asyncio
import logging

from app.cognitive import memory_core, reasoning_log
from app.config import get_settings
from app.db import execute, fetch_one
from app.guardrails import daily_cap, kill_switch
from app.tools import gmail_tool

logger = logging.getLogger(__name__)


class SendRefused(RuntimeError):
    """Raised when a guardrail blocks the send."""


async def send_approved_draft(draft_id: int, approval_id: int) -> int:
    """Send the given draft via Gmail API. Returns sent_log.id.

    Raises:
        SendRefused    if a guardrail blocks.
        RuntimeError   if DB state is inconsistent.
    """
    if kill_switch.is_on():
        raise SendRefused("kill_switch is ON — refusing to send")
    if not daily_cap.try_consume():
        raise SendRefused("daily send cap reached")

    row = fetch_one(
        """
        SELECT d.id AS draft_id, d.subject, d.body, d.email_id, d.sent_status,
               e.from_email, e.gmail_message_id, e.gmail_thread_id, e.subject AS orig_subject,
               e.is_web_form,
               a.decision
          FROM drafts d
          JOIN raw_emails e ON e.id = d.email_id
          JOIN approvals a ON a.id = ?
         WHERE d.id = ?
        """,
        (approval_id, draft_id),
    )
    if not row:
        raise RuntimeError(f"draft {draft_id} or approval {approval_id} missing")
    if row["decision"] != "approved":
        raise SendRefused(f"approval {approval_id} is not 'approved' (is '{row['decision']}')")
    if row["sent_status"] not in ("approved",):
        raise SendRefused(
            f"draft {draft_id} has status '{row['sent_status']}', expected 'approved'"
        )

    # Undo window — Prakash sir has N seconds to flip the approval back.
    await asyncio.sleep(max(get_settings().undo_window_seconds, 0))

    # Re-check that nothing changed during the sleep.
    current = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    if not current or current["sent_status"] != "approved":
        raise SendRefused("draft status changed during undo window — aborting send")

    # Mark sending and do the actual send.
    execute(
        "UPDATE drafts SET sent_status='sending' WHERE id=? AND sent_status='approved'",
        (draft_id,),
    )

    test_mode = get_settings().anika_test_mode
    is_web_form = bool(row.get("is_web_form"))
    gmail_id = ""
    gmail_thread_id = row["gmail_thread_id"]
    if test_mode:
        logger.warning("TEST MODE on — not calling Gmail API for draft %s", draft_id)
    else:
        try:
            # For a regular inbound reply, thread into the original Gmail
            # conversation. For a web-form enquiry, the "original" message
            # lives in Prakash sir's own inbox — threading into it would
            # send the reply back to himself. Start a fresh conversation
            # to the real enquirer instead.
            if is_web_form:
                resp = gmail_tool.send_email(
                    to_email=row["from_email"],
                    subject=row["subject"],
                    body=row["body"],
                )
            else:
                resp = gmail_tool.send_email(
                    to_email=row["from_email"],
                    subject=row["subject"],
                    body=row["body"],
                    thread_id=row["gmail_thread_id"],
                    in_reply_to=row["gmail_message_id"],
                    references=row["gmail_message_id"],
                )
            gmail_id = resp.get("id", "")
            gmail_thread_id = resp.get("threadId", row["gmail_thread_id"])
        except Exception as e:  # noqa: BLE001
            logger.error("Gmail send failed for draft %s: %s", draft_id, e)
            # Rollback status so the operator can retry.
            execute(
                "UPDATE drafts SET sent_status='approved' WHERE id=? AND sent_status='sending'",
                (draft_id,),
            )
            raise

    # Flip to 'sent' — the BEFORE UPDATE trigger will verify the approval row.
    execute(
        "UPDATE drafts SET sent_status='sent' WHERE id=? AND sent_status='sending'",
        (draft_id,),
    )
    cur = execute(
        """
        INSERT INTO sent_log
          (draft_id, email_id, approval_id, gmail_message_id, gmail_thread_id,
           to_email, subject, body, test_mode)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            draft_id,
            row["email_id"],
            approval_id,
            gmail_id,
            gmail_thread_id,
            row["from_email"],
            row["subject"],
            row["body"],
            1 if test_mode else 0,
        ),
    )
    sent_log_id = int(cur.lastrowid)

    # Harvest this send into memory (non-fatal on failure).
    try:
        memory_core.harvest_approved_draft(draft_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("harvest_approved_draft failed for %s: %s", draft_id, e)

    # Phase 1C-1: compute journey metric (non-fatal). Captures edit-distance
    # from Anika's first draft to the approved-and-sent body, per service
    # line, so /train/learning-curves can show real adaptation over time.
    try:
        from app.cognitive.draft_metrics import compute_journey_metric

        compute_journey_metric(int(row["email_id"]), outcome="sent")
    except Exception as e:  # noqa: BLE001
        logger.warning("draft_metrics on send failed for draft %s: %s", draft_id, e)

    reasoning_log.log(
        agent_name="sender",
        input_obj={"draft_id": draft_id, "approval_id": approval_id, "test_mode": test_mode},
        output_obj={"sent_log_id": sent_log_id, "gmail_message_id": gmail_id},
        reasoning_text="sent successfully" if not test_mode else "test-mode send (no gmail API call)",
        draft_id=draft_id,
    )
    return sent_log_id
