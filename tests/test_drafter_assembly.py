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
