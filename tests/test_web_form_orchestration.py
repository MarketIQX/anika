"""End-to-end behaviour tests for the web-form substitution path + the
label-based mark_as_processed replacement for mark_as_read.
"""
from __future__ import annotations

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


def _fake_classifier(cat: str = "new_enquiry"):
    async def _fn(**kwargs):
        from app.db import execute

        out = ClassifierOutput(category=cat, confidence=0.95, reasoning="fake")
        execute(
            "INSERT INTO classifications(email_id, category, confidence, reasoning, model, prompt_version) "
            "VALUES(?,?,?,?,?,?)",
            (kwargs["email_id"], out.category, out.confidence, out.reasoning, "fake", 1),
        )
        # Capture what the classifier was shown — tests assert on this.
        _fn.seen_from_email = kwargs["from_email"]
        _fn.seen_body = kwargs["body_plain"]
        _fn.seen_subject = kwargs["subject"]
        return out

    _fn.seen_from_email = None
    _fn.seen_body = None
    _fn.seen_subject = None
    return _fn


def _fake_enricher():
    async def _fn(**kwargs):
        from app.db import execute
        import json

        out = EnricherOutput(
            sender_name=kwargs.get("from_name", ""),
            sender_org="",
            sender_country="",
            likely_service_line="nri_tax",
            urgency="hot",
            routing_partner="CA Kumar Prasad",
            summary="Fake summary.\nNext: 15-min call.",
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
            (kwargs["email_id"], out.sender_name, out.sender_org, out.sender_country,
             out.likely_service_line, out.urgency, out.routing_partner,
             json.dumps([]), None, out.summary, out.reasoning, "fake", 1),
        )
        return out

    return _fn


def _fake_drafter():
    async def _fn(**kwargs):
        from app.db import execute

        cur = execute(
            """
            INSERT INTO drafts(email_id, parent_draft_id, subject, body, tone_notes,
                               uses_signature, sent_status, model, prompt_version, reasoning)
            VALUES(?,?,?,?,?,1,'pending_approval',?,?,?)
            """,
            (kwargs["email_id"], kwargs.get("parent_draft_id"),
             "Re: Your enquiry to Balakrishna & Co",
             "Dear Ms. X,\n\nThank you.\n\nWarm regards,\nS V Prakasha",
             "warm", "fake", 1, "fake"),
        )
        return int(cur.lastrowid)

    return _fn


def _load_fixture_html() -> str:
    from pathlib import Path
    return (Path(__file__).parent / "fixtures" / "web_form_chandrika.html").read_text(encoding="utf-8")


def _make_web_form_inbox_message() -> InboxMessage:
    """Construct the InboxMessage Gmail would hand us for the Chandrika submission."""
    return InboxMessage(
        message_id="gm-chandrika-1",
        thread_id="th-chandrika-1",
        from_email="prakasha@balakrishnaandco.com",  # mailer sends FROM prakasha
        from_name="BKCO",
        to_email="prakasha@balakrishnaandco.com",
        cc="",
        subject="Balakrishna and Co",
        body_plain="",  # Gmail sometimes supplies only HTML for mailer forms
        body_html=_load_fixture_html(),
        snippet="Congratulation! You receive Want to consult us from chandrika...",
        received_at="2026-04-23T08:00:00Z",
        is_reply_in_thread=False,
    )


@pytest.mark.asyncio
async def test_orchestrator_substitutes_real_enquirer(seeded, monkeypatch):
    fake_cls = _fake_classifier("new_enquiry")
    monkeypatch.setattr(classifier, "classify", fake_cls)
    monkeypatch.setattr(enricher, "enrich", _fake_enricher())
    monkeypatch.setattr(drafter, "draft_reply", _fake_drafter())
    from app.tools import notify_tool

    monkeypatch.setattr(notify_tool, "notify_draft_ready", lambda **kw: True)
    monkeypatch.setattr(notify_tool, "notify_sensitive_bypass", lambda *a, **kw: True)
    monkeypatch.setattr(gmail_tool, "mark_as_processed", lambda *a, **kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    result = await orchestrator.handle(_make_web_form_inbox_message())
    assert result["action"] == "drafted"
    assert result["is_web_form"] is True

    # Classifier was handed the real enquirer, not Prakash sir.
    assert fake_cls.seen_from_email == "chandrika.reddy@example.com"
    assert "NRI currently based in Dubai" in fake_cls.seen_body
    assert fake_cls.seen_subject == "Your enquiry to Balakrishna & Co"

    # raw_emails row stored the substituted sender and the is_web_form=1 flag.
    row = fetch_one("SELECT * FROM raw_emails WHERE gmail_message_id='gm-chandrika-1'")
    assert row is not None
    assert row["from_email"] == "chandrika.reddy@example.com"
    assert row["from_name"] == "Chandrika Reddy"
    assert row["is_web_form"] == 1
    assert row["subject"] == "Your enquiry to Balakrishna & Co"


@pytest.mark.asyncio
async def test_orchestrator_treats_regular_email_normally(seeded, monkeypatch):
    """Sanity: a non-web-form email follows the old path (is_web_form=0)."""
    fake_cls = _fake_classifier("new_enquiry")
    monkeypatch.setattr(classifier, "classify", fake_cls)
    monkeypatch.setattr(enricher, "enrich", _fake_enricher())
    monkeypatch.setattr(drafter, "draft_reply", _fake_drafter())
    from app.tools import notify_tool

    monkeypatch.setattr(notify_tool, "notify_draft_ready", lambda **kw: True)
    monkeypatch.setattr(gmail_tool, "mark_as_processed", lambda *a, **kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    msg = InboxMessage(
        message_id="plain-1", thread_id="t",
        from_email="sarah@acme.com", from_name="Sarah",
        to_email="prakasha@balakrishnaandco.com", cc="",
        subject="India subsidiary help",
        body_plain="Hi, we'd like to set up an Indian subsidiary.",
        body_html="", snippet="", received_at="2026-04-23T09:00:00Z",
        is_reply_in_thread=False,
    )
    result = await orchestrator.handle(msg)
    assert result["action"] == "drafted"
    assert result.get("is_web_form") is False

    row = fetch_one("SELECT is_web_form, from_email FROM raw_emails WHERE gmail_message_id='plain-1'")
    assert row["is_web_form"] == 0
    assert row["from_email"] == "sarah@acme.com"


@pytest.mark.asyncio
async def test_web_form_draft_skips_forced_re_prefix(seeded, monkeypatch):
    """For web forms we don't want the orchestrator to prepend 'Re:' onto the draft
    subject. The fake drafter emits 'Re: Your enquiry to Balakrishna & Co' already;
    the orchestrator should leave it alone."""
    monkeypatch.setattr(classifier, "classify", _fake_classifier("new_enquiry"))
    monkeypatch.setattr(enricher, "enrich", _fake_enricher())
    monkeypatch.setattr(drafter, "draft_reply", _fake_drafter())
    from app.tools import notify_tool

    monkeypatch.setattr(notify_tool, "notify_draft_ready", lambda **kw: True)
    monkeypatch.setattr(gmail_tool, "mark_as_processed", lambda *a, **kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    await orchestrator.handle(_make_web_form_inbox_message())
    drafts = fetch_all("SELECT subject FROM drafts ORDER BY id DESC LIMIT 1")
    # Not 'Re: Re: ...' — the orchestrator didn't double up the prefix.
    assert drafts[0]["subject"].count("Re:") == 1


# --- mark_as_processed behaviour --------------------------------------------


def test_mark_as_processed_does_not_remove_unread(monkeypatch):
    """The critical invariant: no 'removeLabelIds: UNREAD' in the API body."""
    captured: dict = {}

    class FakeModify:
        def execute(self):
            return {}

    class FakeMessages:
        def modify(self, *, userId, id, body):
            captured["userId"] = userId
            captured["id"] = id
            captured["body"] = body
            return FakeModify()

    class FakeUsers:
        def messages(self):
            return FakeMessages()

    class FakeSvc:
        def users(self):
            return FakeUsers()

    monkeypatch.setattr(gmail_tool, "_build_service", lambda: FakeSvc())
    # Short-circuit label resolution so we don't need a real service for it.
    monkeypatch.setattr(gmail_tool, "get_or_create_label", lambda *a, **kw: "Label_42")

    gmail_tool.mark_as_processed("msg-123")

    assert captured["id"] == "msg-123"
    assert captured["body"] == {"addLabelIds": ["Label_42"]}
    # The body must NOT touch UNREAD in any way.
    assert "removeLabelIds" not in captured["body"]
    body_json = str(captured["body"])
    assert "UNREAD" not in body_json


def test_get_or_create_label_reuses_existing(monkeypatch):
    class FakeLabels:
        def list(self, *, userId):
            class Req:
                def execute(_self):
                    return {
                        "labels": [
                            {"id": "Label_existing", "name": "Anika/Processed"},
                            {"id": "Label_other", "name": "Important"},
                        ]
                    }
            return Req()

        def create(self, *, userId, body):
            raise AssertionError("should not create when label exists")

    class FakeUsers:
        def labels(self):
            return FakeLabels()

    class FakeSvc:
        def users(self):
            return FakeUsers()

    monkeypatch.setattr(gmail_tool, "_build_service", lambda: FakeSvc())
    monkeypatch.setattr(gmail_tool, "_PROCESSED_LABEL_ID", None, raising=False)

    lid = gmail_tool.get_or_create_label("Anika/Processed")
    assert lid == "Label_existing"


def test_get_or_create_label_creates_when_missing(monkeypatch):
    created: dict = {}

    class FakeLabels:
        def list(self, *, userId):
            class Req:
                def execute(_self):
                    return {"labels": [{"id": "Label_other", "name": "Misc"}]}
            return Req()

        def create(self, *, userId, body):
            created.update(body)

            class Req:
                def execute(_self):
                    return {"id": "Label_new", **body}
            return Req()

    class FakeUsers:
        def labels(self):
            return FakeLabels()

    class FakeSvc:
        def users(self):
            return FakeUsers()

    monkeypatch.setattr(gmail_tool, "_build_service", lambda: FakeSvc())
    monkeypatch.setattr(gmail_tool, "_PROCESSED_LABEL_ID", None, raising=False)

    lid = gmail_tool.get_or_create_label("Anika/Processed")
    assert lid == "Label_new"
    assert created.get("name") == "Anika/Processed"


# --- Sender threading behaviour for web forms -------------------------------


@pytest.mark.asyncio
async def test_sender_skips_threading_for_web_form(seeded, monkeypatch):
    """is_web_form=1 → send_email called without thread_id / in_reply_to / references."""
    from app.agents import approver
    from app.db import execute

    # Small setup: an approved web-form draft.
    execute(
        """
        INSERT INTO raw_emails
          (gmail_message_id, gmail_thread_id, from_email, to_email, subject,
           received_at, is_web_form)
        VALUES('gm-wf','t-wf','real@enquirer.com','prakasha@balakrishnaandco.com',
               'Your enquiry to Balakrishna & Co','2026-04-23T10:00:00Z',1)
        """
    )
    cur = execute(
        "INSERT INTO drafts(email_id, subject, body, model) VALUES(?,?,?,?)",
        (1, "Re: Your enquiry to Balakrishna & Co", "body text", "gpt-4o"),
    )
    draft_id = int(cur.lastrowid)

    # Flip test mode OFF and stub send_email so we can capture its args.
    from app import config as cfg

    s = cfg.get_settings()
    s.undo_window_seconds = 0
    s.anika_test_mode = False

    captured_kwargs: dict = {}

    def fake_send_email(**kwargs):
        captured_kwargs.update(kwargs)
        return {"id": "sent-gmail-id", "threadId": "sent-thread-id"}

    monkeypatch.setattr(gmail_tool, "send_email", fake_send_email)

    # Approve the draft — this drives Sender.
    await approver.approve(draft_id, decided_by="aks@marketiqx.com")

    # Critical: no threading headers were passed.
    assert captured_kwargs["to_email"] == "real@enquirer.com"
    assert "thread_id" not in captured_kwargs
    assert "in_reply_to" not in captured_kwargs
    assert "references" not in captured_kwargs
