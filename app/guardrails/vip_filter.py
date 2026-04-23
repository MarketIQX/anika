"""VIP filter — skip auto-draft for priority clients.

VIP senders get a summary-only notification to Prakash sir so he handles
them personally. The orchestrator still records the raw email and an
enrichment row, but does not invoke the Drafter.
"""
from __future__ import annotations

from app.tools import client_tool


def should_skip_draft(from_email: str) -> tuple[bool, str]:
    """Return (skip, reason). reason is a short human string."""
    if client_tool.is_vip(from_email):
        return True, "sender flagged VIP — summary-only, handle personally"
    return False, ""
