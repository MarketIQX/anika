"""Offline agent tests — exercise the orchestrator with mocked LLM outputs.

These tests prove the pipeline wiring (classifier -> enricher -> drafter ->
notify) without burning OpenAI calls. We substitute async fakes that return
deterministic structured outputs.
"""
from __future__ import annotations

import json

import pytest

from app.agents import classifier, drafter, enricher, orchestrator
from app.agents.schemas import ClassifierOutput, DrafterOutput, EnricherOutput
from app.db import fetch_all, fetch_one
from app.jobs import backfill_memory
from app.tools import gmail_tool
from app.tools.gmail_tool import InboxMessage


@pytest.fixture
def seeded():
    backfill_memory._seed_firm_knowledge()
    backfill_memory._seed_rules()
    backfill_memory._seed_agent_prompts()


def _fake_classifier(cat="new_enquiry", confidence=0.9):
    async def _fn(**kwargs):
        # Write classification row the way real classifier does.
        from app.db import execute

        out = ClassifierOutput(category=cat, confidence=confidence, reasoning="fake")
        execute(
            "INSERT INTO classifications(email_id, category, confidence, reasoning, model, prompt_version) "
            "VALUES(?,?,?,?,?,?)",
            (kwargs["email_id"], out.category, out.confidence, out.reasoning, "fake", 1),
        )
        return out

    return _fn


def _fake_enricher(service_line="nri_tax", urgency="hot"):
    async def _fn(**kwargs):
        from app.db import execute

        out = EnricherOutput(
            sender_name=kwargs.get("from_name", ""),
            sender_org="",
            sender_country="",
            likely_service_line=service_line,
            urgency=urgency,
            routing_partner="CA Kumar Prasad",
            summary="Test enquiry about NRI taxation.\nNext step: 15-min call.",
            reasoning="fake",
        )
        execute(
            """
            INSERT INTO enrichments
              (email_id, sender_name, sender_org, sender_country, likely_service_line,
               urgency, routing_partner, similar_memories, client_match_id, summary,
               reasoning, model, prompt_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                kwargs["email_id"],
                out.sender_name,
                out.sender_org,
                out.sender_country,
                out.likely_service_line,
                out.urgency,
                out.routing_partner,
                json.dumps([]),
                None,
                out.summary,
                out.reasoning,
                "fake",
                1,
            ),
        )
        return out

    return _fn


def _fake_drafter(body="Dear Mr. X,\n\nThanks for writing in.\n\nWarm regards,\nS V Prakasha"):
    async def _fn(**kwargs):
        from app.db import execute

        cur = execute(
            """
            INSERT INTO drafts(email_id, parent_draft_id, subject, body, tone_notes,
                               uses_signature, sent_status, model, prompt_version, reasoning)
            VALUES(?,?,?,?,?,1,'pending_approval',?,?,?)
            """,
            (
                kwargs["email_id"],
                kwargs.get("parent_draft_id"),
                f"Re: {kwargs['subject']}",
                body,
                "warm + tight",
                "fake",
                1,
                "fake",
            ),
        )
        return int(cur.lastrowid)

    return _fn


def _no_notify(*args, **kwargs):
    return True


@pytest.mark.asyncio
async def test_new_enquiry_produces_draft(seeded, monkeypatch):
    monkeypatch.setattr(classifier, "classify", _fake_classifier("new_enquiry"))
    monkeypatch.setattr(enricher, "enrich", _fake_enricher("nri_tax", "hot"))
    monkeypatch.setattr(drafter, "draft_reply", _fake_drafter())
    # Block the notifier (no Gmail token in tests).
    from app.tools import notify_tool

    monkeypatch.setattr(notify_tool, "notify_draft_ready", _no_notify)
    monkeypatch.setattr(notify_tool, "notify_sensitive_bypass", _no_notify)
    # Don't try to hit Gmail to mark-as-read.
    monkeypatch.setattr(gmail_tool, "mark_as_read", lambda *_a, **_kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    msg = InboxMessage(
        message_id="test-new-1",
        thread_id="t1",
        from_email="rajesh@example.com",
        from_name="Rajesh",
        to_email="prakasha@balakrishnaandco.com",
        cc="",
        subject="NRI ITR help",
        body_plain="Hi, I'm an NRI filing my ITR-2, need help.",
        body_html="",
        snippet="",
        received_at="2026-04-22T10:00:00Z",
        is_reply_in_thread=False,
    )
    result = await orchestrator.handle(msg)
    assert result["action"] == "drafted"
    assert fetch_one("SELECT id FROM drafts WHERE id=?", (result["draft_id"],)) is not None


@pytest.mark.asyncio
async def test_sensitive_email_bypasses_drafter(seeded, monkeypatch):
    monkeypatch.setattr(classifier, "classify", _fake_classifier("sensitive"))
    # Shouldn't even get called:
    monkeypatch.setattr(enricher, "enrich", _fake_enricher())
    monkeypatch.setattr(drafter, "draft_reply", _fake_drafter())
    from app.tools import notify_tool

    monkeypatch.setattr(notify_tool, "notify_draft_ready", _no_notify)
    monkeypatch.setattr(notify_tool, "notify_sensitive_bypass", _no_notify)
    monkeypatch.setattr(gmail_tool, "mark_as_read", lambda *_a, **_kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    msg = InboxMessage(
        message_id="test-sensitive-1",
        thread_id="t2",
        from_email="x@example.com",
        from_name="X",
        to_email="prakasha@balakrishnaandco.com",
        cc="",
        subject="Legal notice from Income Tax",
        body_plain="We received a legal notice, help.",
        body_html="",
        snippet="",
        received_at="2026-04-22T10:00:00Z",
        is_reply_in_thread=False,
    )
    result = await orchestrator.handle(msg)
    assert result["action"] == "bypass_sensitive"
    # No draft should have been written.
    drafts = fetch_all("SELECT * FROM drafts")
    assert drafts == []


@pytest.mark.asyncio
async def test_vip_sender_bypasses_drafter(seeded, monkeypatch):
    from app.tools import client_tool

    client_tool.upsert_client(
        email="vip@example.com", name="VIP", is_vip_flag=True
    )
    monkeypatch.setattr(classifier, "classify", _fake_classifier("new_enquiry"))
    monkeypatch.setattr(enricher, "enrich", _fake_enricher())
    monkeypatch.setattr(drafter, "draft_reply", _fake_drafter())
    from app.tools import notify_tool

    monkeypatch.setattr(notify_tool, "notify_draft_ready", _no_notify)
    monkeypatch.setattr(notify_tool, "notify_sensitive_bypass", _no_notify)
    monkeypatch.setattr(gmail_tool, "mark_as_read", lambda *_a, **_kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    msg = InboxMessage(
        message_id="test-vip-1",
        thread_id="t3",
        from_email="vip@example.com",
        from_name="VIP",
        to_email="prakasha@balakrishnaandco.com",
        cc="",
        subject="NRI question",
        body_plain="Hello",
        body_html="",
        snippet="",
        received_at="2026-04-22T10:00:00Z",
        is_reply_in_thread=False,
    )
    result = await orchestrator.handle(msg)
    assert result["action"] == "bypass_vip"
    assert fetch_all("SELECT id FROM drafts") == []


@pytest.mark.asyncio
async def test_kill_switch_short_circuits(seeded, monkeypatch):
    from app.guardrails import kill_switch

    kill_switch.set_on()
    monkeypatch.setattr(classifier, "classify", _fake_classifier())
    monkeypatch.setattr(gmail_tool, "mark_as_read", lambda *_a, **_kw: None)

    msg = InboxMessage(
        message_id="test-kill-1",
        thread_id="t4",
        from_email="any@example.com",
        from_name="Any",
        to_email="prakasha@balakrishnaandco.com",
        cc="",
        subject="Hi",
        body_plain="Hello",
        body_html="",
        snippet="",
        received_at="2026-04-22T10:00:00Z",
        is_reply_in_thread=False,
    )
    result = await orchestrator.handle(msg)
    assert result["action"] == "skip"
    # Raw email IS ingested even under kill-switch.
    assert fetch_one("SELECT id FROM raw_emails WHERE gmail_message_id='test-kill-1'") is not None
    # But no classification or draft.
    assert fetch_all("SELECT * FROM classifications") == []
    assert fetch_all("SELECT * FROM drafts") == []
