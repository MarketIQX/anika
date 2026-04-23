"""Tests for the Teaching Learner.

We mock the Runner.run call so these tests don't hit OpenAI — the
assertions are about wiring (adaptive limit, output shaping, PII
detection, storage behaviour).
"""
from __future__ import annotations

import pytest

from app.agents.teaching_learner import (
    LearnerClarification,
    LearnerOutput,
    LearnerUnit,
    adaptive_clarification_limit,
    cap_clarifications,
    detect_pii_in_unit,
)


# --- Adaptive clarification limit ------------------------------------------


@pytest.mark.parametrize("n,expected", [
    (0, 3), (1, 3), (5, 3), (10, 3),
    (15, 5), (20, 6), (25, 8),
    (33, 10), (100, 10),  # capped
])
def test_adaptive_clarification_limit(n, expected):
    assert adaptive_clarification_limit(n) == expected


def test_cap_clarifications_splits_surface_and_defer():
    units = [LearnerUnit(kind="rule", content=f"Rule {i}", scope="universal",
                         service_line="", confidence=0.9) for i in range(20)]
    clarifications = [
        LearnerClarification(question_text=f"Q{i}", options=[], target_unit_index=i % 20)
        for i in range(10)
    ]
    out = LearnerOutput(units=units, clarifications=clarifications)
    surface, defer = cap_clarifications(out)
    # 20 units → limit = 6 → 6 surface + 4 deferred.
    assert len(surface) == 6
    assert len(defer) == 4


# --- PII detection ---------------------------------------------------------


def test_pii_detector_spots_phone_email_pan():
    hits = detect_pii_in_unit("Reach me at +91 98765 43210 or foo.bar@example.com. PAN ABCDE1234F.")
    assert "phone" in hits
    assert "email" in hits
    assert "pan" in hits


def test_pii_detector_silent_on_clean_content():
    assert detect_pii_in_unit("This is a plain rule about formal salutation.") == []


# --- Teaching pipeline (with mocked Learner) -------------------------------


@pytest.mark.asyncio
async def test_finalize_queue_stores_unambiguous_units(monkeypatch):
    """Units with no associated clarification flow straight into knowledge_library."""
    from app.agents import teaching_learner
    from app.cognitive import teaching

    async def fake_extract(content, *, source_hint=""):
        # Use PII-free content so the PII auto-clarification doesn't fire.
        return LearnerOutput(
            units=[
                LearnerUnit(kind="rule", content="Always use Indian English spelling.",
                            scope="universal", service_line="", confidence=0.95),
                LearnerUnit(kind="policy",
                            content="Do not quote specific fees in first replies.",
                            scope="universal", service_line="", confidence=0.98),
            ],
            clarifications=[],
        )

    monkeypatch.setattr(teaching_learner, "extract", fake_extract)

    qid = teaching.enqueue_text(raw_content="teach text", created_by="aks@marketiqx.com")
    # Also monkeypatch embed to avoid hitting OpenAI.
    from app.tools import memory_tool as _mt
    monkeypatch.setattr(_mt, "embed", lambda text: [0.0] * 1536)

    summary = await teaching.finalize_queue(qid)
    assert summary["status"] == "approved"
    assert summary["units_added"] == 2

    from app.db import fetch_all
    rows = fetch_all("SELECT kind, content, scope FROM knowledge_library WHERE is_active=1")
    assert len(rows) == 2
    assert {r["kind"] for r in rows} == {"rule", "policy"}
    assert {r["scope"] for r in rows} == {"universal"}


@pytest.mark.asyncio
async def test_finalize_queue_defers_ambiguous_units(monkeypatch):
    """A unit with a paired clarification is NOT stored; its clarification is."""
    from app.agents import teaching_learner
    from app.cognitive import teaching
    from app.db import fetch_all
    from app.tools import memory_tool as _mt

    monkeypatch.setattr(_mt, "embed", lambda text: [0.0] * 1536)

    async def fake_extract(content, *, source_hint=""):
        return LearnerOutput(
            units=[
                LearnerUnit(
                    kind="rule",
                    content="First reply always offers a 15-minute call.",
                    scope="service_line", service_line="",  # blank → ambiguous
                    confidence=0.6,
                ),
            ],
            clarifications=[
                LearnerClarification(
                    question_text="Which service line does this apply to?",
                    options=["nri_tax", "foreign_subsidiary", "all of them (universal)"],
                    target_unit_index=0,
                ),
            ],
        )

    monkeypatch.setattr(teaching_learner, "extract", fake_extract)

    qid = teaching.enqueue_text(raw_content="teach text", created_by="aks@marketiqx.com")
    summary = await teaching.finalize_queue(qid)
    assert summary["status"] == "needs_clarification"
    assert summary["units_added"] == 0
    # Clarification row present.
    c_rows = fetch_all("SELECT * FROM clarifications WHERE queue_id=?", (qid,))
    assert len(c_rows) == 1
    assert "service line" in c_rows[0]["question_text"].lower()
    # Zero library rows.
    k_rows = fetch_all("SELECT * FROM knowledge_library WHERE is_active=1")
    assert k_rows == []


@pytest.mark.asyncio
async def test_finalize_queue_pii_flag_generates_clarification(monkeypatch):
    """A unit containing PII-looking content gets a clarification card even
    if the Learner was confident."""
    from app.agents import teaching_learner
    from app.cognitive import teaching
    from app.db import fetch_all
    from app.tools import memory_tool as _mt

    monkeypatch.setattr(_mt, "embed", lambda text: [0.0] * 1536)

    async def fake_extract(content, *, source_hint=""):
        return LearnerOutput(
            units=[LearnerUnit(
                kind="example",
                content="Dear Mr. Sharma, your PAN ABCDE1234F is registered.",
                scope="universal", service_line="", confidence=0.95,
            )],
            clarifications=[],
        )

    monkeypatch.setattr(teaching_learner, "extract", fake_extract)

    qid = teaching.enqueue_text(raw_content="teach text", created_by="aks@marketiqx.com")
    await teaching.finalize_queue(qid)

    c_rows = fetch_all("SELECT * FROM clarifications WHERE queue_id=?", (qid,))
    assert len(c_rows) == 1
    assert "PII" in c_rows[0]["question_text"]


@pytest.mark.asyncio
async def test_answer_clarification_stores_rule(monkeypatch):
    """Answering a clarification promotes the unit to knowledge_library."""
    from app.cognitive import teaching
    from app.db import execute, fetch_all
    from app.tools import memory_tool as _mt

    monkeypatch.setattr(_mt, "embed", lambda text: [0.0] * 1536)

    # Seed a pending clarification + queue row.
    qid = teaching.enqueue_text(raw_content="raw", created_by="aks@marketiqx.com")
    cur = execute(
        """
        INSERT INTO clarifications
          (queue_id, question_text, options_json, target_unit_index, unit_preview, status)
        VALUES (?, 'Which service?', '[\"nri_tax\",\"foreign_subsidiary\"]', 0,
                'On NRI property sales, always request Form 26AS first.', 'pending')
        """,
        (qid,),
    )
    clar_id = int(cur.lastrowid)

    result = await teaching.answer_clarification(
        clar_id, answer="nri_tax", answered_by="aks@marketiqx.com",
    )
    assert result["action"] == "stored"
    assert result["scope"] == "service_line"

    rows = fetch_all("SELECT * FROM knowledge_library WHERE is_active=1")
    assert len(rows) == 1
    assert rows[0]["service_line"] == "nri_tax"
    assert rows[0]["scope"] == "service_line"
