"""Tests for Phase 1C-3 voice_harvester — embedding-similarity dedup.

These tests focus on the new behavior added in commit 2b: before saving,
the harvester checks whether a near-duplicate active voice_example
already exists in the same scope. If yes, it returns the existing
library_id and creates no new row.

memory_tool.embed is monkeypatched per-test to a deterministic fake:
identical content -> identical vector (distance=0, hits dedup), distinct
content -> orthogonal-ish unit vectors (distance ~sqrt(2), misses dedup).
"""
from __future__ import annotations

import hashlib
import math
import random

import pytest

from app.cognitive import voice_harvester
from app.cognitive.voice_harvester import (
    DEDUP_DISTANCE_THRESHOLD,
    harvest_voice_example,
)
from app.db import EMBEDDING_DIM, execute, fetch_all, fetch_one
from app.tools import memory_tool


# --- Seed helpers ---------------------------------------------------------
# reasoning_log carries FK to raw_emails + drafts. Tests that pass
# source_email_id / source_draft_id must seed matching rows first.


def _seed_email(message_id: str = "m1") -> int:
    cur = execute(
        """
        INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email,
                               to_email, subject, body_plain, received_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        (message_id, f"t-{message_id}", "x@y.com",
         "prakasha@balakrishnaandco.com", "Test", "body", "2026-04-27T10:00:00Z"),
    )
    return int(cur.lastrowid)


def _seed_draft(email_id: int) -> int:
    cur = execute(
        """
        INSERT INTO drafts(email_id, subject, body, model)
        VALUES(?, 'Re: Test', 'placeholder body', 'gpt-4o')
        """,
        (email_id,),
    )
    return int(cur.lastrowid)


def _seeded_ids() -> tuple[int, int]:
    """Return (email_id, draft_id) freshly seeded for use as FK targets."""
    eid = _seed_email(f"m-{random.randint(1, 1_000_000_000)}")
    did = _seed_draft(eid)
    return eid, did


# --- Deterministic embed fake ---------------------------------------------


def _fake_embed(text: str) -> list[float]:
    """Deterministic-per-content unit-normalized vector.

    Same content -> same vector (L2 distance 0).
    Distinct content -> ~orthogonal random unit vectors (L2 distance ~sqrt(2)).
    Empty / whitespace input -> [] (matches real memory_tool.embed).
    """
    text = (text or "").strip()
    if not text:
        return []
    h = hashlib.sha256(text.encode("utf-8")).digest()
    rng = random.Random(h)
    v = [rng.gauss(0.0, 1.0) for _ in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return v
    return [x / norm for x in v]


@pytest.fixture(autouse=True)
def _patch_embed(monkeypatch):
    """Replace OpenAI calls with the deterministic fake for every test."""
    monkeypatch.setattr(memory_tool, "embed", _fake_embed)


# --- Body factory ---------------------------------------------------------


def _body(suffix: str = "") -> str:
    """Make a body comfortably above MIN_BODY_CHARS=50."""
    base = (
        "Dear Vijay, thank you for reaching out regarding your tax matters. "
        "We will be glad to assist with planning and ITR filing."
    )
    return f"{base} {suffix}".strip() if suffix else base


# --- Tests ----------------------------------------------------------------


def test_first_save_creates_new_entry():
    """Cold-start: empty library -> save succeeds and skips the embed call."""
    _, did = _seeded_ids()
    lib_id = harvest_voice_example(
        sent_body=_body(),
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=did,
    )
    assert lib_id is not None
    row = fetch_one(
        "SELECT id, harvest_source, service_line, purpose FROM knowledge_library WHERE id=?",
        (lib_id,),
    )
    assert row is not None
    assert row["harvest_source"] == "edit_approval"
    assert row["service_line"] == "nri_tax"
    assert row["purpose"] == "voice_example"


def test_dedup_blocks_duplicate_save_same_service_line():
    """Second save of identical body + service_line returns the first id, no new row."""
    _, d1 = _seeded_ids()
    e2, _ = _seeded_ids()
    body = _body("alpha")
    first = harvest_voice_example(
        sent_body=body,
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d1,
    )
    assert first is not None
    rows_before = fetch_all(
        "SELECT id FROM knowledge_library WHERE is_active=1 AND purpose='voice_example'"
    )
    assert len(rows_before) == 1

    second = harvest_voice_example(
        sent_body=body,
        service_line="nri_tax",
        created_by="test",
        source="gmail_outbound",
        source_email_id=e2,
    )
    assert second == first  # dedup hit returns the existing id

    rows_after = fetch_all(
        "SELECT id FROM knowledge_library WHERE is_active=1 AND purpose='voice_example'"
    )
    assert len(rows_after) == 1  # no new row


def test_dedup_does_not_block_distinct_content():
    """Different bodies -> different vectors -> both saved."""
    _, d1 = _seeded_ids()
    _, d2 = _seeded_ids()
    a = harvest_voice_example(
        sent_body=_body("alpha"),
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d1,
    )
    b = harvest_voice_example(
        sent_body=_body("beta — entirely different sentence about something else"),
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d2,
    )
    assert a is not None and b is not None
    assert a != b
    rows = fetch_all(
        "SELECT id FROM knowledge_library WHERE is_active=1 AND purpose='voice_example'"
    )
    assert len(rows) == 2


def test_dedup_does_not_cross_service_lines():
    """Same body, different service_line -> NOT deduped (independent signal)."""
    _, d1 = _seeded_ids()
    _, d2 = _seeded_ids()
    body = _body("identical content")
    a = harvest_voice_example(
        sent_body=body,
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d1,
    )
    b = harvest_voice_example(
        sent_body=body,
        service_line="foreign_subsidiary",
        created_by="test",
        source="edit_approval",
        source_draft_id=d2,
    )
    assert a is not None and b is not None
    assert a != b
    rows = fetch_all(
        "SELECT id, service_line FROM knowledge_library "
        "WHERE is_active=1 AND purpose='voice_example' ORDER BY id"
    )
    assert len(rows) == 2
    assert {r["service_line"] for r in rows} == {"nri_tax", "foreign_subsidiary"}


def test_dedup_ignores_soft_deleted_entries():
    """A soft-deleted near-duplicate must NOT prevent a fresh save."""
    from app.cognitive.library import soft_delete_entry

    _, d1 = _seeded_ids()
    _, d2 = _seeded_ids()
    body = _body("zeta")
    first = harvest_voice_example(
        sent_body=body,
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d1,
    )
    assert first is not None
    soft_delete_entry(first, deleted_by="test")

    second = harvest_voice_example(
        sent_body=body,
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d2,
    )
    assert second is not None
    assert second != first  # a fresh row, not the deactivated one

    active = fetch_all(
        "SELECT id FROM knowledge_library WHERE is_active=1 AND purpose='voice_example'"
    )
    assert len(active) == 1
    assert active[0]["id"] == second


def test_dedup_universal_scope_matches_any_service_line():
    """A universal-scope voice_example dedups against any service_line caller.

    voice_harvester saves with scope='universal' when service_line is None,
    so a universal entry can match a later call with any specific
    service_line (the universal entry applies everywhere).
    """
    _, d2 = _seeded_ids()
    body = _body("universal-content")
    universal = harvest_voice_example(
        sent_body=body,
        service_line=None,  # -> scope='universal'
        created_by="test",
        source="manual_upload",
    )
    assert universal is not None

    second = harvest_voice_example(
        sent_body=body,
        service_line="nri_tax",
        created_by="test",
        source="edit_approval",
        source_draft_id=d2,
    )
    assert second == universal

    rows = fetch_all(
        "SELECT id FROM knowledge_library WHERE is_active=1 AND purpose='voice_example'"
    )
    assert len(rows) == 1


def test_threshold_constant_is_documented_value():
    """Sanity: the threshold constant is the documented 0.30 value.

    A change to this constant is allowed but should be a deliberate
    code change reviewed through git, not a quiet drift. This test is
    a tripwire if someone bumps the value without updating the
    docstring math.
    """
    assert DEDUP_DISTANCE_THRESHOLD == 0.30
