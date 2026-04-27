"""Phase 1C-3 — outbound harvester job.

Detects partner replies sent directly via Gmail (bypassing Anika's draft)
and harvests them as voice_examples. Runs once per Gmail poll cycle, after
the inbox loop. Best-effort: per-email errors are logged and skipped, the
poll loop never crashes.

Design principles (from the 1C-3 spec):
  - Read-only on Gmail (no labels, no marks, no mutations).
  - Idempotent (run twice on the same data = no duplicate harvest).
  - Best-effort, never blocks the pipeline.
  - Strip signatures via voice_harvester (which uses firm_identity helpers).
  - Attribution: voice_example knows it came from gmail_outbound.
  - Audit trail in reasoning_log.
  - Silent on success, logger.warning on failure.

Scale bounding:
  - HARVEST_LOOKBACK_DAYS=7: emails older than this are not scanned.
    Beyond 7 days the matching draft is no longer pending and the
    voice_example value is marginal. Extend window only when production
    data shows we're missing valuable harvests.
  - HARVEST_MAX_PER_CYCLE=50: cap Gmail API calls per cycle. Anything
    above this is picked up next cycle.

Idempotency:
  - The scan filter is `outbound_reply_gmail_id IS NULL` — once a row is
    marked, it is never rescanned. We mark even when the harvest is
    skipped (body too short) so we don't repeatedly re-fetch the thread.
  - Multiple partner outbounds in the same thread: only the FIRST
    qualifying message (earliest after the original received_at) is
    harvested; second/third outbounds are deliberately ignored. CA
    workflow: first reply is the substantive answer, follow-ups are
    typically clarifications and not voice signal.
"""
from __future__ import annotations

import logging

from googleapiclient.errors import HttpError

from app.cognitive import reasoning_log
from app.cognitive.voice_harvester import harvest_voice_example
from app.config import get_settings
from app.db import execute, fetch_all, fetch_one
from app.tools import gmail_tool
from app.tools.gmail_tool import InboxMessage

logger = logging.getLogger(__name__)


HARVEST_LOOKBACK_DAYS = 7
HARVEST_MAX_PER_CYCLE = 50

# Body length floor BEFORE handing to voice_harvester. voice_harvester also
# applies MIN_BODY_CHARS=50 after signature strip, but checking here too
# saves an embed call on obvious one-liners ("thanks", "noted", etc.).
HARVEST_MIN_BODY_CHARS = 50


def _partner_email_set() -> set[str]:
    """Parse settings.outbound_harvest_partner_emails into a lowercased set."""
    raw = get_settings().outbound_harvest_partner_emails or ""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _find_partner_outbound(
    messages: list[InboxMessage],
    partner_emails: set[str],
    *,
    after: str,
) -> InboxMessage | None:
    """Return the first thread message that is FROM a partner AND was sent
    strictly after the original `after` timestamp.

    Why "strictly after received_at": the original enquiry might itself have
    been sent BY the partner (e.g., the website-form mailer self-sends).
    We only count partner messages that arrived AFTER the substantive
    enquiry was logged in raw_emails.

    Messages from the Gmail thread API are oldest-first, so the first
    qualifying message is the EARLIEST partner outbound after `after`.

    Comparison on `received_at` is lexical — the InboxMessage timestamps
    and raw_emails.received_at use the same ISO-8601 UTC format
    ("%Y-%m-%dT%H:%M:%fZ"), so string comparison is correct.
    """
    for m in messages:
        if not m.received_at or m.received_at <= after:
            continue
        from_lc = (m.from_email or "").strip().lower()
        if from_lc in partner_emails:
            return m
    return None


async def harvest_outbound_replies() -> dict[str, int]:
    """Scan recently-received emails for partner outbound replies; harvest each.

    Per-cycle counters returned for observability:
      harvested            — voice_example saved (or dedup hit) AND row marked
      skipped_no_outbound  — thread had no qualifying partner reply
      skipped_too_short    — partner reply body below threshold; row marked anyway
      errors               — per-email failures (Gmail API, harvest call, etc.)

    Plus optional flags:
      no_credentials, no_partner_emails_configured

    Best-effort: any per-email failure is caught, logged, and the next email
    proceeds. The function never raises into the caller (poll_gmail loop).
    """
    if not gmail_tool.has_credentials():
        return {
            "harvested": 0,
            "skipped_no_outbound": 0,
            "skipped_too_short": 0,
            "errors": 0,
            "no_credentials": 1,
        }

    partner_emails = _partner_email_set()
    if not partner_emails:
        logger.warning(
            "outbound_harvester: no partner emails configured — "
            "settings.outbound_harvest_partner_emails is empty. Skipping cycle."
        )
        return {
            "harvested": 0,
            "skipped_no_outbound": 0,
            "skipped_too_short": 0,
            "errors": 0,
            "no_partner_emails_configured": 1,
        }

    counters = {
        "harvested": 0,
        "skipped_no_outbound": 0,
        "skipped_too_short": 0,
        "errors": 0,
    }

    rows = fetch_all(
        f"""
        SELECT id, gmail_thread_id, received_at
          FROM raw_emails
         WHERE outbound_reply_gmail_id IS NULL
           AND gmail_thread_id IS NOT NULL
           AND gmail_thread_id != ''
           AND received_at > strftime(
               '%Y-%m-%dT%H:%M:%fZ', 'now', '-{HARVEST_LOOKBACK_DAYS} days'
           )
         ORDER BY received_at DESC
         LIMIT ?
        """,
        (HARVEST_MAX_PER_CYCLE,),
    )

    for row in rows:
        email_id = int(row["id"])
        thread_id = row["gmail_thread_id"]
        original_received_at = row["received_at"]

        try:
            messages = gmail_tool.get_thread(thread_id)
        except HttpError as e:
            logger.warning(
                "outbound_harvester: get_thread failed for thread=%s email_id=%s: %s",
                thread_id, email_id, e,
            )
            counters["errors"] += 1
            continue
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "outbound_harvester: unexpected get_thread failure for thread=%s email_id=%s: %s",
                thread_id, email_id, e,
            )
            counters["errors"] += 1
            continue

        partner_msg = _find_partner_outbound(
            messages, partner_emails, after=original_received_at
        )
        if partner_msg is None:
            counters["skipped_no_outbound"] += 1
            continue

        partner_body = (partner_msg.body_plain or "").strip()
        if len(partner_body) < HARVEST_MIN_BODY_CHARS:
            counters["skipped_too_short"] += 1
            # Mark scanned anyway so we don't re-fetch this thread next cycle.
            execute(
                """UPDATE raw_emails
                      SET outbound_reply_gmail_id = ?,
                          outbound_reply_harvested_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                    WHERE id = ?""",
                (partner_msg.message_id, email_id),
            )
            continue

        en = fetch_one(
            "SELECT likely_service_line FROM enrichments "
            "WHERE email_id = ? ORDER BY id DESC LIMIT 1",
            (email_id,),
        )
        service_line = (en or {}).get("likely_service_line")

        try:
            library_id = harvest_voice_example(
                sent_body=partner_body,
                service_line=service_line,
                created_by="outbound_harvester",
                source="gmail_outbound",
                source_email_id=email_id,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "outbound_harvester: harvest_voice_example failed for email %s: %s",
                email_id, e,
            )
            counters["errors"] += 1
            continue

        # Mark the email as harvested even when library_id is None (dedup
        # hit returns existing id; embed failures return None). The same
        # outbound message must not be re-harvested next cycle.
        execute(
            """UPDATE raw_emails
                  SET outbound_reply_gmail_id = ?,
                      outbound_reply_harvested_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE id = ?""",
            (partner_msg.message_id, email_id),
        )

        # If Anika has a pending draft for this email, flip its status so
        # the dashboard reflects what really happened: the partner went
        # around Anika.
        pending = fetch_one(
            "SELECT id FROM drafts WHERE email_id=? AND sent_status='pending_approval' LIMIT 1",
            (email_id,),
        )
        pending_draft_id = int(pending["id"]) if pending else None
        if pending_draft_id is not None:
            execute(
                "UPDATE drafts SET sent_status='rejected_partner_replied_outside' WHERE id=?",
                (pending_draft_id,),
            )

        reasoning_log.log(
            agent_name="outbound_harvester",
            input_obj={
                "email_id": email_id,
                "gmail_thread_id": thread_id,
                "partner_message_id": partner_msg.message_id,
                "service_line": service_line,
            },
            output_obj={
                "library_id": library_id,
                "draft_marked_replied_outside": pending_draft_id,
            },
            email_id=email_id,
            draft_id=pending_draft_id,
        )
        counters["harvested"] += 1

    if counters["harvested"] or counters["errors"]:
        logger.info("outbound_harvester cycle: %s", counters)
    return counters
