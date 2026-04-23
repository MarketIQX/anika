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

    subject = f"Anika: draft ready for approval ({tag}{sl})"
    body = (
        f"New enquiry summary:\n"
        f"{sender_summary.strip()}\n\n"
        f"Review & approve: {url}\n\n"
        f"— Anika"
    )

    try:
        gmail_tool.send_email(get_settings().notify_email, subject, body)
        logger.info("Notification sent for draft %s", draft_id)
        return True
    except Exception as e:  # noqa: BLE001 — we want all failures logged, never raised to caller
        logger.error("Failed to send notification for draft %s: %s", draft_id, e)
        return False


def notify_sensitive_bypass(email_id: int, from_email: str, subject: str, reason: str) -> bool:
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
