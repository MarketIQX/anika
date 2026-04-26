"""Approval notification — send Prakash sir a 1-line email with dashboard link.

Replaces the Telegram approval card. On every pending draft, we fire a short
email that links to the Drafts tab. Prakash sir approves/edits/rejects there.

Why email (not Telegram):
- Zero extra setup (no bot token, no chat-id handshake).
- He already lives in his inbox — low-friction.
- The email can't send the reply itself; the dashboard still enforces the
  database approval gate.
"""
from __future__ import annotations

import logging

from app.config import get_settings
from app.tools import gmail_tool

logger = logging.getLogger(__name__)


def _draft_url(draft_id: int) -> str:
    base = get_settings().anika_public_base_url.rstrip("/")
    return f"{base}/drafts/{draft_id}"


def notify_draft_ready(
    draft_id: int,
    sender_summary: str,
    service_line: str | None,
    urgency: str | None,
) -> bool:
    """Send a 1-line approval-ready email to the configured notify address.

    Args:
        draft_id: the drafts.id to link to.
        sender_summary: 2-line enricher summary (shown inline).
        service_line: matched service line ("nri_tax" etc.) or None.
        urgency: 'hot' | 'warm' | 'cold' | None.

    Returns:
        True if Gmail accepted the send, False otherwise (error logged).
    """
    url = _draft_url(draft_id)
    tag = urgency.upper() if urgency else "NEW"
    sl = f" [{service_line}]" if service_line else ""

    # Cognitive state from the draft row
    from app.db import fetch_one as _fetch_one
    cog_row = _fetch_one(
        "SELECT cognitive_state, voice_coverage_count FROM drafts WHERE id = ?",
        (draft_id,),
    )
    cognitive_state = cog_row["cognitive_state"] if cog_row else None
    voice_count = cog_row["voice_coverage_count"] if cog_row else 0

    cold_marker = " - TEACH ME" if cognitive_state == "cold_start" else ""
    subject = f"Anika: draft ready for approval ({tag}{sl}){cold_marker}"

    if cognitive_state == "cold_start":
        sl_name = service_line or "this service line"
        honesty_preamble = (
            f"COLD START - first draft for {sl_name}\n\n"
            f"I have no learned voice examples for this area yet. This draft is my "
            f"best-guess, conservative interpretation - not your actual voice.\n\n"
            f"What to do: edit the draft to your actual style before approving. "
            f"Your edit becomes my first voice example for {sl_name}, "
            f"and future drafts in this area will learn from it.\n\n"
        )
    elif cognitive_state == "learning":
        sl_name = service_line or "this service line"
        honesty_preamble = (
            f"LEARNING - I have {voice_count} voice example(s) for {sl_name}.\n"
            f"Still early in learning. Please review carefully - each edit sharpens my voice.\n\n"
        )
    else:
        honesty_preamble = ""

    body = (
        f"{honesty_preamble}"
        f"New enquiry summary:\n"
        f"{sender_summary.strip()}\n\n"
        f"Review & approve: {url}\n\n"
        f"- Anika"
    )
    try:
        gmail_tool.send_email(get_settings().notify_email, subject, body)
        logger.info("Notification sent for draft %s", draft_id)
        return True
    except Exception as e:  # noqa: BLE001 — we want all failures logged, never raised to caller
        logger.error("Failed to send notification for draft %s: %s", draft_id, e)
        return False


def notify_sensitive_bypass(
    email_id: int,
    from_email: str,
    subject: str,
    reason: str,
) -> bool:
    """Alert Prakash sir when Anika has bypassed an enquiry as 'sensitive'.

    No draft is created; this is a priority flag for manual handling.
    """
    base = get_settings().anika_public_base_url.rstrip("/")
    url = f"{base}/inbox/{email_id}"
    subj = f"Anika: sensitive enquiry — please handle directly"
    body = (
        f"Sir, Anika detected a sensitive enquiry and did not draft a reply.\n\n"
        f"From:    {from_email}\n"
        f"Subject: {subject}\n"
        f"Reason:  {reason}\n\n"
        f"Open in Anika: {url}\n\n"
        f"— Anika"
    )
    try:
        gmail_tool.send_email(get_settings().notify_email, subj, body)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to send sensitive-bypass notification: %s", e)
        return False
