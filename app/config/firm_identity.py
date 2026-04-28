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


# Email domains owned by the firm. Inbound mail from any address at one
# of these domains is INTERNAL correspondence (a colleague, the partner
# himself, an internal alias) — never a client enquiry — and must be
# filtered by the structural validator before any LLM call.
#
# Bug: prior to this list existing, draft 43 was generated in reply to
# csprashant@balakrishnaandco.com — a colleague's mail — because the
# validator had no internal-domain check. Fixed by importing FIRM_DOMAINS
# in app/guardrails/structural_validator.py.
#
# Adding a new firm domain is a code change reviewed through git, same
# discipline as SIGNATURE_BLOCK above.
FIRM_DOMAINS: frozenset[str] = frozenset({
    "balakrishnaandco.com",
})


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


# Markers that indicate the start of a signature / sign-off block. The list
# is canonical here so the approver, the outbound harvester, and any future
# voice-example consumer share one definition. We cut the body at the
# EARLIEST marker found and rstrip the result.
#
# Each marker begins with "\n" so we never accidentally cut mid-paragraph
# on a sign-off word that happens to occur in the body text. Adding a new
# marker is a code change reviewed through git, not a runtime knob.
SIGNATURE_MARKERS: tuple[str, ...] = (
    "\nWarm regards,",
    "\nBest regards,",
    "\nYours faithfully,",
    "\nRegards,",
    "\nSincerely,",
    "\nS V Prakasha",
    "\nCA Prakasha",
    "\nCA S V Prakasha",
)


def strip_signature_block(body: str) -> str:
    """Return `body` with the trailing signature/sign-off block removed.

    Cuts at the earliest occurrence of any SIGNATURE_MARKERS entry and
    rstrip()s the result. Used before persisting voice_examples so the
    saved content teaches BODY voice only — the canonical signature is
    re-appended at draft time by ensure_signature(), so leaking signature
    text into voice_examples would cause double-sig on retrieval.

    Returns body unchanged if no marker is found.
    """
    if not body:
        return ""
    cut_at = len(body)
    for marker in SIGNATURE_MARKERS:
        idx = body.find(marker)
        if 0 <= idx < cut_at:
            cut_at = idx
    if cut_at < len(body):
        return body[:cut_at].rstrip()
    return body
