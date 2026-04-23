"""Locked firm identity — the signature block and naming facts that must
NEVER be changed at runtime or via the dashboard.

Why constants in code (not a DB row):
  - The signature appears on every outbound email. If an LLM, a compromised
    session, or a well-meaning admin could edit it, an attacker could
    exfiltrate or spoof identity by adding a fake "ATTN:" line.
  - Storing it as Python source means any change is a code change, which
    passes through git review and pre-commit hooks.
  - The Drafter is instructed to append the signature block verbatim; the
    orchestrator re-validates that the draft body ends with this exact block
    before Sender is allowed to send.

Any attempt to mutate these via API returns 403 — see app/dashboard/routes.py.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# DO NOT CHANGE THE VALUES IN THIS FILE FROM A RUNTIME CONTEXT.
# Edit the source, commit through code review, restart Anika.
# ---------------------------------------------------------------------------

SIGNATURE_BLOCK: str = """Yours faithfully,
CA Prakasha
Partner, Balakrishna & Co. | BKPS & Co LLP
Chartered Accountants
Phone: 8618259712
Email: prakasha@balakrishnaandco.com"""

FIRM_NAME: str = "Balakrishna & Co."
FIRM_PARTNER_NAME: str = "CA Prakasha"


def signature_matches(body: str) -> bool:
    """Return True if `body` ends with SIGNATURE_BLOCK verbatim (trailing
    whitespace tolerated). Used by the Sender as a last-line-of-defence
    check before any draft is sent.
    """
    if not body:
        return False
    return body.rstrip().endswith(SIGNATURE_BLOCK.rstrip())


def ensure_signature(body: str) -> str:
    """Return `body` guaranteed to end with the exact signature block.

    If the body already ends with it (whitespace-tolerant), returned
    as-is. Otherwise the canonical block is appended after a blank line.
    The Drafter also targets this via its prompt; this is a backstop.
    """
    if signature_matches(body):
        return body
    return f"{body.rstrip()}\n\n{SIGNATURE_BLOCK}"
