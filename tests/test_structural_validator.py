"""Unit tests for app.guardrails.structural_validator.

Production gap surfaced by draft 43: csprashant@balakrishnaandco.com
(a colleague at the firm) was treated as an external enquirer because
the validator had no internal-domain check. Anika drafted a reply to
internal mail. Fix imports FIRM_DOMAINS from firm_identity and rejects
those senders before any LLM call.
"""
from __future__ import annotations

from app.guardrails.structural_validator import validate


def test_internal_partner_email_filtered():
    """Mail from any FIRM_DOMAINS sender is filtered as
    'internal_partner_email' — never reaches the orchestrator's LLM
    pipeline."""
    ok, reason = validate(
        from_email="csprashant@balakrishnaandco.com",
        subject="quick chat about the Mehta file",
        body_plain=(
            "Hi Prakasha, can we sync this afternoon on the Mehta NRI "
            "matter? I have the form 26AS download ready."
        ),
        raw_headers=None,
        is_web_form=False,
    )
    assert ok is False
    assert reason == "internal_partner_email"


def test_external_client_still_passes():
    """Regression guard: the new internal-domain filter must not reject
    legitimate external enquiries."""
    ok, reason = validate(
        from_email="rajesh@example.com",
        subject="NRI ITR help",
        body_plain=(
            "Hi, I'm an NRI based in Dubai filing my ITR-2 for FY24-25, "
            "need help with foreign income reporting."
        ),
        raw_headers=None,
        is_web_form=False,
    )
    assert ok is True
    assert reason == "ok"
