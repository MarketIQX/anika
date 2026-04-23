"""Weekly review — rolling 7-day summary of Anika activity.

Generates a plain-text summary the dashboard can render or email. Not
auto-scheduled in v2; the dashboard Settings tab has a "Generate this
week's review" button that calls `build_summary()`.
"""
from __future__ import annotations

from app.db import fetch_all, fetch_one


def build_summary() -> dict[str, int | list[dict]]:
    """Return a dict with weekly counts and a short incidents list."""
    total = fetch_one(
        "SELECT COUNT(*) n FROM raw_emails WHERE received_at >= datetime('now','-7 days')"
    )["n"]
    classified = fetch_all(
        """
        SELECT category, COUNT(*) n FROM classifications
         WHERE created_at >= datetime('now','-7 days')
         GROUP BY category
        """
    )
    drafted = fetch_one(
        """
        SELECT COUNT(*) n FROM drafts
         WHERE created_at >= datetime('now','-7 days')
        """
    )["n"]
    approved = fetch_one(
        """
        SELECT COUNT(*) n FROM approvals
         WHERE decision='approved' AND created_at >= datetime('now','-7 days')
        """
    )["n"]
    edited = fetch_one(
        """
        SELECT COUNT(*) n FROM approvals
         WHERE decision='edited' AND created_at >= datetime('now','-7 days')
        """
    )["n"]
    rejected = fetch_one(
        """
        SELECT COUNT(*) n FROM approvals
         WHERE decision='rejected' AND created_at >= datetime('now','-7 days')
        """
    )["n"]
    sent = fetch_one(
        """
        SELECT COUNT(*) n FROM sent_log
         WHERE sent_at >= datetime('now','-7 days')
        """
    )["n"]
    errors = fetch_all(
        """
        SELECT agent_name, error_text, created_at
          FROM reasoning_log
         WHERE status='error' AND created_at >= datetime('now','-7 days')
         ORDER BY created_at DESC
         LIMIT 20
        """
    )

    return {
        "total_emails_7d": int(total),
        "classified_breakdown": [dict(c) for c in classified],
        "drafts_7d": int(drafted),
        "approved_7d": int(approved),
        "edited_7d": int(edited),
        "rejected_7d": int(rejected),
        "sent_7d": int(sent),
        "errors_7d": [dict(e) for e in errors],
    }
