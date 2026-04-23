"""Tests for the learning engine — edit delta + prompt evolution.

We don't hit OpenAI here. classify_edit is exercised in an offline test by
monkeypatching the OpenAI call.
"""
from __future__ import annotations

import pytest

from app.cognitive import learning_engine
from app.db import execute, fetch_all, fetch_one
from app.jobs import backfill_memory


def test_compute_delta_similarity():
    before = "Dear Mr. Smith, happy to help."
    after = "Dear Mr. Smith, happy to help with your India entry."
    d = learning_engine.compute_delta(before, after)
    assert 0 < d["similarity"] < 1.0
    assert any(c["op"] == "insert" for c in d["changes"])


def test_evolve_drafter_prompt_creates_new_version():
    backfill_memory._seed_agent_prompts()
    before = fetch_one(
        "SELECT version FROM agent_prompts WHERE agent_name='drafter' AND is_active=1"
    )
    new_id = learning_engine.evolve_drafter_prompt(
        style_rule="Use 'we' instead of 'I' when speaking for the firm.",
        change_note="test",
    )
    after = fetch_one(
        "SELECT id, version, is_active FROM agent_prompts WHERE id=?", (new_id,)
    )
    assert after["is_active"] == 1
    assert after["version"] == (int(before["version"]) + 1)
    # Only one drafter row should be active
    active = fetch_all(
        "SELECT id FROM agent_prompts WHERE agent_name='drafter' AND is_active=1"
    )
    assert len(active) == 1


def test_on_edit_style_path_flips_prompt(monkeypatch):
    backfill_memory._seed_agent_prompts()

    def fake_classify(*args, **kwargs):
        return learning_engine.EditClassification(
            category="style",
            rationale="test",
            style_rule="Always mention MSI Global Alliance once per reply.",
        )

    monkeypatch.setattr(learning_engine, "classify_edit", fake_classify)

    # Seed a draft + approval row to satisfy FK constraints
    cur = execute(
        "INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email, to_email, received_at) "
        "VALUES('mx','tx','a@b.com','prakasha@balakrishnaandco.com','2026-04-22T00:00:00Z')"
    )
    email_id = int(cur.lastrowid)
    cur = execute(
        "INSERT INTO drafts(email_id, subject, body, model) VALUES(?,?,?,?)",
        (email_id, "subj", "orig body", "gpt-4o"),
    )
    draft_id = int(cur.lastrowid)
    cur = execute(
        "INSERT INTO approvals(draft_id, decision, decided_by) VALUES(?,?,?)",
        (draft_id, "edited", "prakasha"),
    )
    approval_id = int(cur.lastrowid)

    before_active = fetch_one(
        "SELECT version FROM agent_prompts WHERE agent_name='drafter' AND is_active=1"
    )
    result = learning_engine.on_edit(
        draft_id=draft_id,
        original_body="orig body",
        edited_body="revised body with MSI Global Alliance mention",
        edit_instruction="Please mention MSI every reply",
        approval_id=approval_id,
    )
    assert result["category"] == "style"
    assert "evolved_drafter_prompt" in result["actions"]
    after_active = fetch_one(
        "SELECT version FROM agent_prompts WHERE agent_name='drafter' AND is_active=1"
    )
    assert int(after_active["version"]) == int(before_active["version"]) + 1


def test_on_edit_context_does_not_evolve_prompt(monkeypatch):
    backfill_memory._seed_agent_prompts()

    def fake_classify(*args, **kwargs):
        return learning_engine.EditClassification(
            category="context",
            rationale="thread-specific reference",
        )

    monkeypatch.setattr(learning_engine, "classify_edit", fake_classify)

    cur = execute(
        "INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email, to_email, received_at) "
        "VALUES('my','ty','a@b.com','prakasha@balakrishnaandco.com','2026-04-22T00:00:00Z')"
    )
    email_id = int(cur.lastrowid)
    cur = execute(
        "INSERT INTO drafts(email_id, subject, body, model) VALUES(?,?,?,?)",
        (email_id, "subj", "orig body", "gpt-4o"),
    )
    draft_id = int(cur.lastrowid)
    cur = execute(
        "INSERT INTO approvals(draft_id, decision, decided_by) VALUES(?,?,?)",
        (draft_id, "edited", "prakasha"),
    )
    approval_id = int(cur.lastrowid)

    before = fetch_one(
        "SELECT version FROM agent_prompts WHERE agent_name='drafter' AND is_active=1"
    )
    result = learning_engine.on_edit(
        draft_id=draft_id,
        original_body="orig body",
        edited_body="orig body with thread-specific nod",
        edit_instruction=None,
        approval_id=approval_id,
    )
    assert result["category"] == "context"
    assert result["actions"] == []  # nothing learned globally
    after = fetch_one(
        "SELECT version FROM agent_prompts WHERE agent_name='drafter' AND is_active=1"
    )
    assert int(after["version"]) == int(before["version"])
