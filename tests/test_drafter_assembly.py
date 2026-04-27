"""Tests for runtime Drafter prompt assembly and its interplay with the
knowledge_library.
"""
from __future__ import annotations

import pytest

from app.agents import drafter
from app.cognitive import library as kb
from app.config import SIGNATURE_BLOCK, FIRM_PARTNER_NAME
from app.config.firm_identity import ensure_signature, signature_matches
from app.db import fetch_one


@pytest.fixture
def embed_mock(monkeypatch):
    """Stub embeddings — we aren't testing vector math here."""
    from app.tools import memory_tool as _mt

    monkeypatch.setattr(_mt, "embed", lambda text: [0.0] * 1536)


# --- Signature-block lock --------------------------------------------------


def test_signature_block_is_a_constant_in_firm_identity():
    """SIGNATURE_BLOCK is importable only from app.config.firm_identity.

    A simple assertion: the value appears exactly once in the source tree
    — we skip the check here and rely on the migration verify step that
    grep-confirms uniqueness.  The runtime guarantee is the ensure_signature
    helper in firm_identity.
    """
    assert FIRM_PARTNER_NAME == "CA Prakasha"
    assert "Yours faithfully," in SIGNATURE_BLOCK
    assert "CA Prakasha" in SIGNATURE_BLOCK


def test_ensure_signature_idempotent():
    body = "Dear Sir,\n\nThanks.\n\n" + SIGNATURE_BLOCK
    assert signature_matches(body)
    assert ensure_signature(body) == body


def test_ensure_signature_appends_if_missing():
    body = "Dear Sir,\n\nThanks."
    out = ensure_signature(body)
    assert signature_matches(out)
    # Didn't duplicate.
    assert out.count("Yours faithfully,") == 1


# --- Prompt assembly -------------------------------------------------------


def test_assemble_prompt_always_ends_with_signature_instruction(embed_mock):
    prompt, ids, _coverage = drafter.assemble_prompt(
        service_line="nri_tax",
        enquiry_body="Question about ITR-2 filing for NRI.",
    )
    assert SIGNATURE_BLOCK in prompt
    # And the schema instruction is below the signature.
    sig_idx = prompt.index(SIGNATURE_BLOCK)
    schema_idx = prompt.index("DrafterOutput")
    assert schema_idx > sig_idx
    # Empty library → no used ids.
    assert ids == []


def test_assemble_prompt_pulls_universal_and_service_rules(embed_mock):
    """retrieve_rules returns universal + matching service_line rules."""
    kb.add_entry(kind="rule", content="Universal: Indian English spelling.",
                 service_line=None, scope="universal", confidence=1.0)
    kb.add_entry(kind="rule",
                 content="NRI: always request Form 26AS first.",
                 service_line="nri_tax", scope="service_line", confidence=1.0)
    kb.add_entry(kind="rule",
                 content="TP: always request prior TP study if any.",
                 service_line="transfer_pricing", scope="service_line", confidence=1.0)

    prompt, ids, _coverage = drafter.assemble_prompt(
        service_line="nri_tax",
        enquiry_body="NRI ITR enquiry",
    )
    assert "Indian English spelling" in prompt
    assert "Form 26AS" in prompt
    assert "prior TP study" not in prompt
    # Both universal + nri_tax rule came through.
    assert len(ids) >= 2


def test_assemble_prompt_retrieves_examples_via_embedding(embed_mock):
    """The examples section should include stored examples for the service."""
    kb.add_entry(
        kind="example",
        content="Dear Sir,\n\nThank you for your note about NRI ITR-2. Could you share Form 26AS?\n\nYours faithfully,\nCA Prakasha",
        service_line="nri_tax", scope="service_line", confidence=1.0,
    )
    prompt, ids, _coverage = drafter.assemble_prompt(
        service_line="nri_tax",
        enquiry_body="NRI looking for ITR-2 help",
    )
    assert "Form 26AS" in prompt
    assert "EXAMPLES OF CA PRAKASHA" in prompt
    assert len(ids) >= 1


def test_applied_counter_bumps(embed_mock):
    """library.bump_applied increments applied_count and stamps last_used_at."""
    lid = kb.add_entry(kind="fact", content="Office in Bangalore.",
                       service_line=None, scope="universal", confidence=1.0)
    row_before = fetch_one("SELECT applied_count, last_used_at FROM knowledge_library WHERE id=?", (lid,))
    assert row_before["applied_count"] == 0
    assert row_before["last_used_at"] is None
    kb.bump_applied([lid])
    row_after = fetch_one("SELECT applied_count, last_used_at FROM knowledge_library WHERE id=?", (lid,))
    assert row_after["applied_count"] == 1
    assert row_after["last_used_at"] is not None


# --- Grounding discipline (1C-3 follow-up bugs) --------------------------
#
# Two real bugs were surfaced after phase-1c-3-harvester landed: drafts 36
# and 29 (cognitive_state='learning') quoted "Rs. 7,500 plus GST" and
# fabricated "1,500 clients across 30 countries". The bug class is
# CONFABULATION — Anika invented specifics with no grounding source — not
# "she said the wrong tokens." A real CA partner DOES quote real fees and
# real credentials when they exist in firm knowledge; what they don't do
# is invent them.
#
# The architectural fix is "ground or generalize": specifics are valid
# only when they appear verbatim in retrieved firm_facts, voice_examples,
# or rules. Otherwise the model uses unspecific language. These tests
# lock that framing in the prompt; a future edit that quietly reverts to
# blanket forbidding (or quietly drops the grounding rule) will fail.


def test_drafter_header_uses_grounding_discipline_not_blanket_forbid():
    """Phase 1C-3 follow-up: HARD RULES must require 'ground or generalize',
    not blanket-forbid currency tokens. Earlier draft prompted with 'almost
    always do not quote specific fees' which the model exploited; an
    over-correction to absolute forbid would have blocked legitimate fee
    quotes once firm_knowledge accrued real fees."""
    txt = drafter.DRAFTER_HEADER
    assert "HARD RULES:" in txt
    hard_rules_section = txt.split("HARD RULES:", 1)[1]
    txt_lower = hard_rules_section.lower()
    # The architectural framing must be present.
    assert "ground or generalize" in txt_lower
    assert "never invent" in txt_lower
    # Grounding requires retrieved-context-verbatim.
    assert "verbatim" in txt_lower
    assert "retrieved" in txt_lower
    # Unspecific fallback language must be modeled in the prompt.
    assert "depend on scope" in txt_lower
    # The "almost always" hedge that the original model exploited is gone.
    assert "almost always" not in txt.lower()


def test_drafter_header_mirror_section_grounds_fee_disclosure_in_examples():
    """The Mirror section must tell the model: mirror what the examples do
    on fees — quote what they quote, generalize what they generalize. NOT
    a blanket 'never quote'."""
    txt = drafter.DRAFTER_HEADER
    mirror_section = txt.split("Mirror from the retrieved examples:", 1)[1]
    mirror_lower = mirror_section.lower()
    assert "fee disclosure" in mirror_lower
    # Framing is "mirror examples", not "never quote".
    assert "verbatim" in mirror_lower or "mirror" in mirror_lower


def test_learning_banner_requires_grounding_not_blanket_forbid(embed_mock):
    """'learning' state: specifics must be grounded in retrieved voice
    examples or firm_facts. One voice_example is not enough to invent
    specifics it doesn't contain. The banner must NOT blanket-forbid
    currency or credentials — it must require grounding."""
    # Seed exactly one voice_example so coverage reads 'learning' (1 < 3).
    kb.add_entry(
        kind="example",
        content="Dear Sir,\n\nA prior NRI reply demonstrating voice.\n\nYours faithfully,\nCA Prakasha",
        service_line="nri_tax",
        scope="service_line",
        confidence=1.0,
    )
    prompt, _ids, coverage = drafter.assemble_prompt(
        service_line="nri_tax",
        enquiry_body="NRI tax + EPF query",
    )
    assert coverage["cognitive_state"] == "learning"
    assert "COGNITIVE STATE: LEARNING" in prompt
    prompt_lower = prompt.lower()
    # Grounding language present.
    assert "ground or generalize" in prompt_lower
    assert "verbatim" in prompt_lower
    # Unspecific fallbacks modeled.
    assert "depend on scope" in prompt_lower


def test_cold_start_banner_still_intact(embed_mock):
    """Regression: cold_start banner is unchanged by this fix (its
    blanket-forbid framing remains correct because in cold_start there
    are by definition no service-line voice_examples to ground from —
    default-unspecific is the right answer there)."""
    # Empty library → cold_start.
    prompt, _ids, coverage = drafter.assemble_prompt(
        service_line="nri_tax",
        enquiry_body="anything",
    )
    assert coverage["cognitive_state"] == "cold_start"
    assert "COGNITIVE STATE: COLD START" in prompt
    # The existing cold_start anti-marketing language is preserved.
    assert "Do NOT quote firm credentials" in prompt


# --- Library retrieval helpers --------------------------------------------


def test_retrieve_rules_skips_inactive_entries(embed_mock):
    lid = kb.add_entry(kind="rule", content="Old rule that will be deleted.",
                       service_line=None, scope="universal", confidence=1.0)
    assert any(r["id"] == lid for r in kb.retrieve_rules(service_line=None))
    kb.soft_delete_entry(lid, deleted_by="tester@x.com")
    assert all(r["id"] != lid for r in kb.retrieve_rules(service_line=None))


def test_retrieve_rules_returns_only_matching_service_line(embed_mock):
    kb.add_entry(kind="rule", content="GST rule", service_line="gst_indirect",
                 scope="service_line", confidence=1.0)
    rows = kb.retrieve_rules(service_line="nri_tax")
    # GST rule should NOT appear for an NRI lookup.
    assert all(r.get("service_line") != "gst_indirect" for r in rows)
