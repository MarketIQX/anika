"""Approver flow — approve / edit / reject, end-to-end with mocked sub-agents."""
from __future__ import annotations

import pytest

from app.agents import approver, drafter, sender
from app.db import execute, fetch_one
from app.jobs import backfill_memory


@pytest.fixture
def seeded():
    backfill_memory._seed_firm_knowledge()
    backfill_memory._seed_rules()
    backfill_memory._seed_agent_prompts()


def _seed_draft() -> tuple[int, int]:
    cur = execute(
        "INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email, from_name, to_email, subject, body_plain, received_at) "
        "VALUES('gm1','t1','rajesh@example.com','Rajesh','prakasha@balakrishnaandco.com','NRI ITR','Need ITR help','2026-04-22T10:00:00Z')"
    )
    email_id = int(cur.lastrowid)
    cur = execute(
        "INSERT INTO drafts(email_id, subject, body, model) VALUES(?,?,?,?)",
        (email_id, "Re: NRI ITR", "Dear Mr. Rajesh,\n\nHappy to help.\n\nWarm regards,\nS V Prakasha", "gpt-4o"),
    )
    draft_id = int(cur.lastrowid)
    # Minimal enrichment row so approver.edit() can reconstruct EnricherOutput.
    execute(
        """
        INSERT INTO enrichments(email_id, likely_service_line, urgency, routing_partner,
                                summary, reasoning, model, prompt_version)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (email_id, "nri_tax", "warm", "CA Kumar Prasad", "sum", "r", "fake", 1),
    )
    return email_id, draft_id


@pytest.mark.asyncio
async def test_reject_path_sets_status_and_logs(seeded):
    _, draft_id = _seed_draft()
    approval_id = approver.reject(draft_id, note="too generic")
    row = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    assert row["sent_status"] == "rejected"
    arow = fetch_one("SELECT decision, edit_instruction FROM approvals WHERE id=?", (approval_id,))
    assert arow["decision"] == "rejected"
    assert arow["edit_instruction"] == "too generic"


@pytest.mark.asyncio
async def test_edit_path_creates_new_pending_draft(seeded, monkeypatch):
    _, draft_id = _seed_draft()

    async def fake_draft(**kwargs):
        cur = execute(
            """
            INSERT INTO drafts(email_id, parent_draft_id, subject, body, tone_notes,
                               uses_signature, sent_status, model, prompt_version, reasoning)
            VALUES(?,?,?,?,?,1,'pending_approval',?,?,?)
            """,
            (
                kwargs["email_id"],
                kwargs.get("parent_draft_id"),
                "Re: NRI ITR",
                "Dear Mr. Rajesh,\n\nMore formal version. MSI mentioned.\n\nWarm regards,\nS V Prakasha",
                "formal",
                "fake",
                1,
                "fake",
            ),
        )
        return int(cur.lastrowid)

    monkeypatch.setattr(drafter, "draft_reply", fake_draft)
    # Stub the learner so we don't call OpenAI.
    from app.cognitive import learning_engine

    monkeypatch.setattr(
        learning_engine,
        "classify_edit",
        lambda *a, **k: learning_engine.EditClassification(category="style", rationale="fake", style_rule="Be formal."),
    )

    new_id = await approver.edit(draft_id, edit_instruction="Make it more formal; mention MSI.")
    assert new_id != draft_id
    new_row = fetch_one("SELECT sent_status, parent_draft_id FROM drafts WHERE id=?", (new_id,))
    assert new_row["sent_status"] == "pending_approval"
    assert new_row["parent_draft_id"] == draft_id
    orig_row = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    assert orig_row["sent_status"] == "edited"


@pytest.mark.asyncio
async def test_approve_path_fires_sender_and_writes_sent_log(seeded):
    # Zero undo window + test mode so we don't wait or call Gmail.
    # Mutate the conftest-shared test settings — it's the same instance in every
    # module that does `from app.config import get_settings`.
    from app.agents import sender as sender_mod

    s = sender_mod.get_settings()
    s.undo_window_seconds = 0
    s.anika_test_mode = True

    _, draft_id = _seed_draft()
    result = await approver.approve(draft_id)
    assert "sent_log_id" in result
    row = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    assert row["sent_status"] == "sent"
    srow = fetch_one("SELECT test_mode FROM sent_log WHERE id=?", (result["sent_log_id"],))
    assert int(srow["test_mode"]) == 1
