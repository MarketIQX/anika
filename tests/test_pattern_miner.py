"""Tests for Phase 1C-2 pattern recognition (pattern_miner)."""
from __future__ import annotations

import json

import pytest

from app.cognitive.draft_metrics import compute_journey_metric
from app.cognitive.pattern_miner import (
    counts_by_status,
    dismiss,
    list_open_patterns,
    mine_patterns,
    promote,
    _diff_ngrams,
    _ngrams,
    _tokenize,
)
from app.db import execute, fetch_all, fetch_one


# --- Helpers ---------------------------------------------------------------


def _make_email(message_id: str = "m1") -> int:
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


def _make_enrichment(email_id: int, service_line: str = "nri_tax") -> None:
    execute(
        """
        INSERT INTO enrichments(email_id, likely_service_line, urgency,
                                routing_partner, summary, reasoning, model)
        VALUES(?,?,?,?,?,?,?)
        """,
        (email_id, service_line, "warm", "CA Kumar Prasad", "sum", "r", "fake"),
    )


def _make_draft(email_id: int, body: str, *, parent_draft_id: int | None = None,
                sent_status: str = "pending_approval") -> int:
    cur = execute(
        """
        INSERT INTO drafts(email_id, parent_draft_id, subject, body, model,
                           sent_status, cognitive_state, voice_coverage_count)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (email_id, parent_draft_id, "Re: Test", body, "gpt-4o",
         sent_status, "cold_start", 0),
    )
    return int(cur.lastrowid)


def _make_approval(draft_id: int, decision: str = "approved") -> int:
    cur = execute(
        "INSERT INTO approvals(draft_id, decision, decided_by) VALUES(?,?,?)",
        (draft_id, decision, "test"),
    )
    return int(cur.lastrowid)


def _seed_journey(
    sl: str,
    first_body: str,
    final_body: str,
    *,
    outcome: str = "sent",
    message_id: str = "m1",
) -> int:
    """Build email + enrichment + first/final drafts + approvals + metric."""
    eid = _make_email(message_id)
    _make_enrichment(eid, sl)
    first = _make_draft(eid, first_body, sent_status="edited")
    _make_approval(first, "edited")
    final = _make_draft(
        eid, final_body, parent_draft_id=first,
        sent_status=outcome,
    )
    _make_approval(final, "approved" if outcome == "sent" else "rejected")
    compute_journey_metric(eid, outcome=outcome)  # type: ignore[arg-type]
    return eid


# --- N-gram primitives -----------------------------------------------------


def test_tokenize_strips_punct_and_lowercases():
    assert _tokenize("Hello, World! 1234 it's") == ["hello", "world", "it's"]


def test_ngrams_skip_pure_stop_phrases():
    """A 3-gram of all stop-words is dropped — pure noise."""
    grams = _ngrams(["the", "and", "of", "audit"])
    # 'the and of' should NOT appear (all-stop)
    assert "the and of" not in grams
    # 'and of audit' has a real token, must appear
    assert "and of audit" in grams


def test_ngrams_size_band():
    toks = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
    grams = _ngrams(toks)
    sizes = {len(g.split()) for g in grams}
    assert sizes == {3, 4, 5, 6, 7}


def test_diff_finds_only_changed_phrases():
    root = "I hope this email finds you well, please find the audit report"
    final = "Please find the audit report attached for your review"
    removed, added = _diff_ngrams(root, final)
    # An n-gram unique to root → removed
    assert any("hope this email finds" in r for r in removed)
    # An n-gram unique to final → added
    assert any("for your review" in a for a in added)
    # An n-gram present in both → in neither set
    assert not any("the audit report" == g for g in removed)


# --- Aggregation + persistence --------------------------------------------


def test_single_journey_below_threshold_does_not_persist():
    """One journey alone can't satisfy MIN_OCCURRENCES (=2). Nothing surfaces."""
    _seed_journey(
        "nri_tax",
        "I hope this email finds you well",
        "Hello — happy to help",
        message_id="m-single",
    )
    counters = mine_patterns()  # full re-mine
    assert counters["inserted"] == 0
    assert counters["below_threshold"] >= 1
    assert list_open_patterns() == []


def test_two_journeys_with_shared_removal_surfaces_pattern():
    """Same removed phrase across 2 journeys → appears as open pattern."""
    shared = "I hope this email finds you well"
    _seed_journey(
        "nri_tax",
        f"{shared}, regarding your ITR question…",
        "Happy to help with your ITR — let's schedule a call",
        message_id="m-A",
    )
    _seed_journey(
        "nri_tax",
        f"{shared}, regarding the FATCA filing…",
        "Happy to take this on — quick call to align?",
        message_id="m-B",
    )
    mine_patterns()
    open_p = list_open_patterns()
    # At least the 7-gram of the shared phrase must be present
    matched = [p for p in open_p if shared.lower() in p["pattern_text"]]
    assert matched, f"expected to find '{shared}' in open patterns, got: {open_p}"
    p = matched[0]
    assert p["pattern_kind"] == "removed_phrase"
    assert p["service_line"] == "nri_tax"
    assert p["occurrences"] >= 2
    # Sample email ids should reference both journeys
    sample_ids = json.loads(p["sample_email_ids"])
    assert len(sample_ids) == 2


def test_remine_is_idempotent():
    """Running the miner twice over the same data must not duplicate rows."""
    shared = "warm regards and thanks for reaching out"
    _seed_journey("audit", f"{shared}. Please share the docs.",
                  "Thanks — please share the docs", message_id="m-id-A")
    _seed_journey("audit", f"{shared}. Could you send the trial balance?",
                  "Could you share the trial balance?", message_id="m-id-B")
    mine_patterns()
    first = fetch_all("SELECT id, occurrences FROM patterns_log WHERE status='open'")
    mine_patterns()  # re-run
    second = fetch_all("SELECT id, occurrences FROM patterns_log WHERE status='open'")
    # Same number of rows, same ids — no duplicates from the UNIQUE constraint.
    assert len(first) == len(second)
    assert {r["id"] for r in first} == {r["id"] for r in second}


def test_per_journey_hook_uses_global_history():
    """When called with email_id, the miner still sees the full history so a
    journey can transition from below-threshold to surfaced as count grows."""
    shared = "I hope you are doing well"
    eid_a = _seed_journey("nri_tax", f"{shared}. About your TDS.",
                          "Happy to help — about your TDS",
                          message_id="m-hook-A")
    # After one journey there's nothing.
    counters = mine_patterns(email_id=eid_a)
    assert counters.get("inserted", 0) == 0

    eid_b = _seed_journey("nri_tax", f"{shared}. About the GST notice.",
                          "Happy to help on the GST notice",
                          message_id="m-hook-B")
    # After the second one, the per-journey hook should now surface the pattern.
    counters = mine_patterns(email_id=eid_b)
    assert counters.get("inserted", 0) >= 1
    assert any(shared.lower() in p["pattern_text"] for p in list_open_patterns())


# --- Lifecycle (dismiss / promote) ----------------------------------------


def test_dismiss_removes_from_open_and_blocks_remine():
    """Dismissed patterns are not re-opened by the miner."""
    shared = "let me know if you have any questions"
    _seed_journey("nri_tax", f"hey there. {shared}.",
                  "hey there.", message_id="m-dis-A")
    _seed_journey("nri_tax", f"hello again. {shared}.",
                  "hello again.", message_id="m-dis-B")
    mine_patterns()
    open_p = list_open_patterns()
    assert open_p, "expected an open pattern before dismiss"
    pid = open_p[0]["id"]
    assert dismiss(pid) is True

    # Dismissed pattern is no longer 'open'
    assert not any(p["id"] == pid for p in list_open_patterns())
    # Status sticks
    row = fetch_one("SELECT status FROM patterns_log WHERE id=?", (pid,))
    assert row["status"] == "dismissed"

    # Re-mining must NOT reopen it
    mine_patterns()
    row2 = fetch_one("SELECT status FROM patterns_log WHERE id=?", (pid,))
    assert row2["status"] == "dismissed"


def test_promote_creates_meta_rule_and_links_pattern():
    shared = "thank you so much for your patience"
    _seed_journey("audit", f"hi. {shared}. attached the report.",
                  "hi — attached the report.", message_id="m-pro-A")
    _seed_journey("audit", f"morning. {shared}. attached the response.",
                  "morning — attached the response.", message_id="m-pro-B")
    mine_patterns()
    open_p = list_open_patterns()
    pid = open_p[0]["id"]
    meta_rule_id = promote(pid)
    assert meta_rule_id > 0

    # patterns_log row updated
    row = fetch_one(
        "SELECT status, promoted_to_meta_rule_id FROM patterns_log WHERE id=?",
        (pid,),
    )
    assert row["status"] == "promoted"
    assert row["promoted_to_meta_rule_id"] == meta_rule_id

    # meta_rules row exists with sensible content
    mr = fetch_one("SELECT * FROM meta_rules WHERE id=?", (meta_rule_id,))
    assert mr is not None
    assert mr["target_purpose"] == "voice_example"
    assert mr["target_service_line"] == "audit"
    assert mr["created_by"] == "pattern_miner"
    assert "audit" in mr["rule_text"].lower()


def test_promote_on_already_promoted_pattern_raises():
    shared = "kindly find attached the relevant documents"
    _seed_journey("audit", f"{shared}.", "find attached.", message_id="m-pp-A")
    _seed_journey("audit", f"{shared} herewith.", "attached.", message_id="m-pp-B")
    mine_patterns()
    pid = list_open_patterns()[0]["id"]
    promote(pid)
    with pytest.raises(ValueError):
        promote(pid)


# --- Status counts ---------------------------------------------------------


def test_counts_by_status_reflects_lifecycle():
    """After one promote + one dismiss, counts must match."""
    # Two patterns
    _seed_journey("nri_tax", "alpha phrase appears here please attached",
                  "thanks", message_id="m-cs-A")
    _seed_journey("nri_tax", "alpha phrase appears here please attached",
                  "thanks", message_id="m-cs-B")
    _seed_journey("audit", "beta phrase shows up consistently here",
                  "got it", message_id="m-cs-C")
    _seed_journey("audit", "beta phrase shows up consistently here",
                  "got it", message_id="m-cs-D")
    mine_patterns()
    open_ids = [p["id"] for p in list_open_patterns()]
    assert len(open_ids) >= 2
    promote(open_ids[0])
    dismiss(open_ids[1])
    counts = counts_by_status()
    assert counts["promoted"] >= 1
    assert counts["dismissed"] >= 1
