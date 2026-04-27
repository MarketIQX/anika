"""Tests for Phase 1C-1 self-measurement (draft_metrics)."""
from __future__ import annotations

import pytest

from app.cognitive.draft_metrics import (
    compute_journey_metric,
    per_service_line_summary,
    recent_metrics,
)
from app.db import execute, fetch_all, fetch_one


# --- Helpers ---------------------------------------------------------------


def _make_email(message_id: str = "m1", **overrides) -> int:
    cur = execute(
        """
        INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email,
                               to_email, subject, body_plain, received_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            message_id, f"t-{message_id}",
            overrides.get("from_email", "x@y.com"),
            overrides.get("to_email", "prakasha@balakrishnaandco.com"),
            overrides.get("subject", "Test"),
            overrides.get("body_plain", "Some body"),
            overrides.get("received_at", "2026-04-27T10:00:00Z"),
        ),
    )
    return int(cur.lastrowid)


def _make_enrichment(email_id: int, service_line: str = "nri_tax") -> int:
    cur = execute(
        """
        INSERT INTO enrichments(email_id, likely_service_line, urgency,
                                routing_partner, summary, reasoning, model)
        VALUES(?,?,?,?,?,?,?)
        """,
        (email_id, service_line, "warm", "CA Kumar Prasad", "sum", "r", "fake"),
    )
    return int(cur.lastrowid)


def _make_draft(
    email_id: int,
    body: str,
    *,
    parent_draft_id: int | None = None,
    cognitive_state: str | None = "cold_start",
    voice_coverage_count: int = 0,
    sent_status: str = "pending_approval",
) -> int:
    cur = execute(
        """
        INSERT INTO drafts(email_id, parent_draft_id, subject, body, model,
                           sent_status, cognitive_state, voice_coverage_count)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            email_id, parent_draft_id, "Re: Test", body, "gpt-4o",
            sent_status, cognitive_state, voice_coverage_count,
        ),
    )
    return int(cur.lastrowid)


def _make_approval(draft_id: int, decision: str = "approved") -> int:
    cur = execute(
        """
        INSERT INTO approvals(draft_id, decision, decided_by)
        VALUES(?,?,?)
        """,
        (draft_id, decision, "test"),
    )
    return int(cur.lastrowid)


# --- Tests -----------------------------------------------------------------


def test_journey_single_draft_sent_records_zero_distance():
    """A draft approved on first try → edit_distance=0, chain_length=1."""
    eid = _make_email("m-single-1")
    _make_enrichment(eid, "nri_tax")
    body = (
        "Dear Sir, thank you for your enquiry. Happy to help with your ITR "
        "filing. Could we schedule a 15-minute call?\n\nYours faithfully,\nCA Prakasha"
    )
    did = _make_draft(eid, body, cognitive_state="cold_start", sent_status="sent")
    _make_approval(did, "approved")

    metric_id = compute_journey_metric(eid, outcome="sent")
    assert metric_id is not None
    row = fetch_one("SELECT * FROM draft_metrics WHERE id=?", (metric_id,))
    assert row["email_id"] == eid
    assert row["first_draft_id"] == did
    assert row["final_draft_id"] == did
    assert row["final_outcome"] == "sent"
    assert row["service_line"] == "nri_tax"
    assert row["cognitive_state"] == "cold_start"
    assert row["chain_length"] == 1
    assert row["edit_distance"] == 0.0
    assert row["similarity_ratio"] == 1.0


def test_journey_edit_chain_records_real_distance():
    """First draft → edit → second draft (substantially different) → approve.
    edit_distance should be > 0 because final body differs from first."""
    eid = _make_email("m-chain-1")
    _make_enrichment(eid, "foreign_subsidiary")
    first_body = "Dear Mr. Smith, happy to help with your India entry."
    second_body = (
        "Dear Mr. Smith, thank you for the detailed brief. Setting up an "
        "Indian subsidiary involves several steps that we have streamlined "
        "over 37 years and 150+ foreign companies. Let us schedule a "
        "20-minute call this week."
    )
    first_id = _make_draft(eid, first_body, cognitive_state="learning",
                            voice_coverage_count=2, sent_status="edited")
    second_id = _make_draft(eid, second_body, parent_draft_id=first_id,
                             cognitive_state="learning", voice_coverage_count=2,
                             sent_status="sent")
    _make_approval(first_id, "edited")
    _make_approval(second_id, "approved")

    metric_id = compute_journey_metric(eid, outcome="sent")
    assert metric_id is not None
    row = fetch_one("SELECT * FROM draft_metrics WHERE id=?", (metric_id,))
    assert row["first_draft_id"] == first_id
    assert row["final_draft_id"] == second_id
    assert row["chain_length"] == 2
    assert row["edit_distance"] > 0.1, (
        f"expected substantial edit_distance, got {row['edit_distance']}"
    )
    assert row["edit_distance"] < 1.0
    # Cognitive state snapshotted from FIRST draft, even though the chain
    # could have transitioned during the edit.
    assert row["cognitive_state"] == "learning"


def test_journey_rejected_records_metric_with_outcome_rejected():
    eid = _make_email("m-reject-1")
    _make_enrichment(eid, "audit")
    body = "Some draft that was rejected"
    did = _make_draft(eid, body, cognitive_state="cold_start", sent_status="rejected")
    _make_approval(did, "rejected")

    metric_id = compute_journey_metric(eid, outcome="rejected")
    assert metric_id is not None
    row = fetch_one("SELECT * FROM draft_metrics WHERE id=?", (metric_id,))
    assert row["final_outcome"] == "rejected"
    assert row["service_line"] == "audit"
    # First draft = final draft for a single-shot reject.
    assert row["edit_distance"] == 0.0


def test_compute_journey_metric_is_idempotent():
    """Running twice on the same (email, outcome) returns the SAME row id."""
    eid = _make_email("m-idem-1")
    _make_enrichment(eid, "nri_tax")
    did = _make_draft(eid, "body", sent_status="sent")
    _make_approval(did, "approved")

    a = compute_journey_metric(eid, outcome="sent")
    b = compute_journey_metric(eid, outcome="sent")
    assert a == b
    rows = fetch_all("SELECT id FROM draft_metrics WHERE email_id=? AND final_outcome='sent'", (eid,))
    assert len(rows) == 1


def test_compute_journey_metric_returns_none_when_no_first_draft():
    eid = _make_email("m-empty-1")
    # No draft exists for this email.
    metric_id = compute_journey_metric(eid, outcome="sent")
    assert metric_id is None
    assert fetch_all("SELECT id FROM draft_metrics WHERE email_id=?", (eid,)) == []


def test_per_service_line_summary_aggregates_correctly():
    """Multiple metrics across two service lines produce the right summary."""
    # Service line A: 3 sent (mostly low distance), 1 rejected
    for i, body in enumerate([
        "First draft text version one of this email. " * 3,
        "First draft text version two of this email. " * 3,
        "First draft text version three of this email. " * 3,
    ]):
        eid = _make_email(f"m-A-{i}")
        _make_enrichment(eid, "nri_tax")
        did = _make_draft(eid, body, sent_status="sent")
        _make_approval(did, "approved")
        compute_journey_metric(eid, outcome="sent")

    eid = _make_email("m-A-rej")
    _make_enrichment(eid, "nri_tax")
    did = _make_draft(eid, "rejected body", sent_status="rejected")
    _make_approval(did, "rejected")
    compute_journey_metric(eid, outcome="rejected")

    # Service line B: 2 sent
    for i, body in enumerate(["B body 1 short", "B body 2 short"]):
        eid = _make_email(f"m-B-{i}")
        _make_enrichment(eid, "foreign_subsidiary")
        did = _make_draft(eid, body, sent_status="sent")
        _make_approval(did, "approved")
        compute_journey_metric(eid, outcome="sent")

    summary = per_service_line_summary()
    by_sl = {s["service_line"]: s for s in summary}
    assert "nri_tax" in by_sl
    assert "foreign_subsidiary" in by_sl
    assert by_sl["nri_tax"]["sent_count"] == 3
    assert by_sl["nri_tax"]["rejected_count"] == 1
    assert by_sl["foreign_subsidiary"]["sent_count"] == 2
    # Mean is computed from sent only — rejected doesn't dilute.
    assert by_sl["nri_tax"]["all_time_mean"] == 0.0  # all single-shot, identical first==final
    assert by_sl["foreign_subsidiary"]["all_time_mean"] == 0.0


def test_recent_metrics_returns_in_reverse_chronological_order():
    eids = []
    for i in range(3):
        eid = _make_email(f"m-recent-{i}")
        _make_enrichment(eid, "gst_indirect")
        did = _make_draft(eid, f"body {i}", sent_status="sent")
        _make_approval(did, "approved")
        compute_journey_metric(eid, outcome="sent")
        eids.append(eid)

    rows = recent_metrics(limit=3)
    # Most recent first → metrics for email 2, 1, 0 in that order.
    assert [r["email_id"] for r in rows] == list(reversed(eids))


def test_journey_metric_persists_voice_coverage_count():
    eid = _make_email("m-vcc-1")
    _make_enrichment(eid, "transfer_pricing")
    did = _make_draft(eid, "body", cognitive_state="learned", voice_coverage_count=7,
                       sent_status="sent")
    _make_approval(did, "approved")
    metric_id = compute_journey_metric(eid, outcome="sent")
    row = fetch_one("SELECT * FROM draft_metrics WHERE id=?", (metric_id,))
    assert row["voice_coverage_count"] == 7
    assert row["cognitive_state"] == "learned"


def test_per_service_line_summary_trend_improving():
    """Earlier metrics have higher edit_distance, recent ones lower → improving."""
    # Earlier 3 metrics: high edit distance (different first/final bodies).
    for i in range(3):
        eid = _make_email(f"m-trend-old-{i}")
        _make_enrichment(eid, "virtual_cfo")
        first_body = "Short stub draft"
        final_body = "A very different and substantially longer draft body. " * 5
        first_id = _make_draft(eid, first_body, sent_status="edited")
        second_id = _make_draft(eid, final_body, parent_draft_id=first_id, sent_status="sent")
        _make_approval(first_id, "edited")
        _make_approval(second_id, "approved")
        compute_journey_metric(eid, outcome="sent")

    # Recent 5 metrics: low edit distance (first == final).
    for i in range(5):
        eid = _make_email(f"m-trend-new-{i}")
        _make_enrichment(eid, "virtual_cfo")
        body = f"Identical draft text version with index {i}. " * 5
        did = _make_draft(eid, body, sent_status="sent")
        _make_approval(did, "approved")
        compute_journey_metric(eid, outcome="sent")

    summary = per_service_line_summary()
    cfo = next(s for s in summary if s["service_line"] == "virtual_cfo")
    assert cfo["sent_count"] == 8
    # Recent 5 are 0.0 edit_distance (first==final). Earlier 3 are >0.
    # → trend should be 'improving'.
    assert cfo["trend"] == "improving"
