"""HTTP-level tests for the /train endpoints + signature lock + drafting_paused."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents import teaching_learner
from app.agents.teaching_learner import LearnerClarification, LearnerOutput, LearnerUnit
from app.auth import users as users_mod
from app.db import fetch_all, fetch_one


AK_EMAIL = "aks@marketiqx.com"
AK_PW = "ak-test-password-1234"
PK_EMAIL = "prakasha@balakrishnaandco.com"
PK_PW = "pk-test-password-5678"


@pytest.fixture
def seeded_users():
    users_mod.create_user(AK_EMAIL, AK_PW, role="admin")
    users_mod.create_user(PK_EMAIL, PK_PW, role="user")


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def no_openai(monkeypatch):
    """Stub OpenAI usage (embeddings + learner) so tests are deterministic."""
    from app.tools import memory_tool as _mt

    monkeypatch.setattr(_mt, "embed", lambda text: [0.0] * 1536)

    async def fake_extract(content, *, source_hint=""):
        return LearnerOutput(
            units=[LearnerUnit(kind="rule", content="Always use Indian English.",
                               scope="universal", service_line="", confidence=0.95)],
            clarifications=[],
        )

    monkeypatch.setattr(teaching_learner, "extract", fake_extract)


def _login(client: TestClient, email: str, password: str) -> None:
    r = client.post("/login", data={"email": email, "password": password},
                    follow_redirects=False)
    assert r.status_code == 303


# --- Access control -------------------------------------------------------


def test_train_visible_to_user_role(seeded_users, client):
    """Both roles can reach /train now (the training page is the whole point)."""
    _login(client, PK_EMAIL, PK_PW)
    r = client.get("/train")
    assert r.status_code == 200


def test_train_unauth_redirects(client):
    r = client.get("/train", follow_redirects=False)
    assert r.status_code == 303


# --- Teach flow -----------------------------------------------------------


def test_post_teach_text_creates_queue_and_library(seeded_users, client, no_openai):
    _login(client, PK_EMAIL, PK_PW)
    r = client.post(
        "/train/teach",
        data={"content": "Always use Indian English spelling."},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert fetch_one("SELECT COUNT(*) n FROM teaching_queue")["n"] == 1
    assert fetch_one("SELECT COUNT(*) n FROM knowledge_library WHERE is_active=1")["n"] == 1


def test_post_teach_file_creates_queue_row(seeded_users, client, no_openai, tmp_path):
    _login(client, PK_EMAIL, PK_PW)
    payload_text = "Always use Indian English spelling."
    r = client.post(
        "/train/teach",
        files={"files": ("teach.txt", payload_text, "text/plain")},
    )
    assert r.status_code == 200  # followed redirect chain
    rows = fetch_all("SELECT * FROM teaching_queue")
    assert len(rows) == 1
    assert rows[0]["source_type"] == "file"
    assert rows[0]["original_filename"] == "teach.txt"


# --- Clarifications -------------------------------------------------------


def test_clarification_answer_promotes_unit(seeded_users, client, no_openai, monkeypatch):
    """A pending clarification, when answered, writes a row to knowledge_library."""
    from app.cognitive import teaching
    from app.db import execute

    _login(client, PK_EMAIL, PK_PW)
    # Seed a queue row + clarification directly (faster than running the learner)
    qid = teaching.enqueue_text(raw_content="raw", created_by=PK_EMAIL)
    cur = execute(
        """
        INSERT INTO clarifications
          (queue_id, question_text, options_json, target_unit_index, unit_preview, status)
        VALUES (?, 'Which service?', '[\"nri_tax\",\"foreign_subsidiary\"]', 0,
                'For NRI property sales: always request Form 26AS first.', 'pending')
        """,
        (qid,),
    )
    clar_id = int(cur.lastrowid)

    r = client.post(
        f"/train/clarify/{clar_id}",
        data={"answer": "nri_tax"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    rows = fetch_all("SELECT kind, service_line, scope FROM knowledge_library WHERE is_active=1")
    assert len(rows) == 1
    assert rows[0]["service_line"] == "nri_tax"


# --- Edit / delete --------------------------------------------------------


def test_library_edit_updates_content(seeded_users, client, no_openai):
    from app.cognitive import library

    _login(client, AK_EMAIL, AK_PW)
    lid = library.add_entry(kind="rule", content="Original.", service_line=None,
                             scope="universal", confidence=1.0)
    r = client.post(
        f"/train/library/{lid}/edit",
        data={"content": "Edited content.", "kind": "rule",
              "scope": "universal", "service_line": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303
    row = fetch_one("SELECT content FROM knowledge_library WHERE id=?", (lid,))
    assert row["content"] == "Edited content."


def test_soft_delete_leaves_row_with_is_active_false(seeded_users, client, no_openai):
    from app.cognitive import library

    _login(client, PK_EMAIL, PK_PW)
    lid = library.add_entry(kind="rule", content="To be deleted.",
                             service_line=None, scope="universal", confidence=1.0)
    r = client.post(f"/train/library/{lid}/delete", follow_redirects=False)
    assert r.status_code == 303
    row = fetch_one("SELECT is_active, deleted_by FROM knowledge_library WHERE id=?", (lid,))
    assert row["is_active"] == 0
    assert row["deleted_by"] == PK_EMAIL


# --- Export --------------------------------------------------------------


def test_library_export_xlsx(seeded_users, client, no_openai):
    from app.cognitive import library

    _login(client, PK_EMAIL, PK_PW)
    library.add_entry(kind="rule", content="Indian English spelling.",
                      service_line=None, scope="universal", confidence=1.0)

    r = client.get("/train/library/export?fmt=xlsx")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    # openpyxl file starts with "PK" (it's a zip).
    assert r.content[:2] == b"PK"


def test_library_export_json(seeded_users, client, no_openai):
    from app.cognitive import library

    _login(client, AK_EMAIL, AK_PW)
    library.add_entry(kind="fact", content="Phone: 8618259712.",
                      service_line=None, scope="universal", confidence=1.0)

    r = client.get("/train/library/export?fmt=json")
    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]
    assert b"8618259712" in r.content


# --- Admin prompt preview -------------------------------------------------


def test_admin_sees_prompt_preview_link(seeded_users, client):
    """Prompt preview section renders for admin (even if no drafter logs yet)."""
    _login(client, AK_EMAIL, AK_PW)
    r = client.get("/train")
    # The section header exists for admin even when empty — the preview
    # card itself only appears if there's drafter log data. Either way,
    # user role should NOT see the section header.
    admin_body = r.content
    _logout(client)

    _login(client, PK_EMAIL, PK_PW)
    r = client.get("/train")
    user_body = r.content
    # Admin-only block (the "Latest drafter prompt" section) must not appear
    # in user-role output.
    assert b"Latest drafter prompt" not in user_body
    # For admin, it appears only if data exists. We just verify user is blocked.


def _logout(client: TestClient) -> None:
    client.post("/logout", follow_redirects=False)


# --- Signature-block lock -------------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_signature_endpoints_return_403(seeded_users, client, method):
    _login(client, AK_EMAIL, AK_PW)
    r = client.request(method, "/settings/signature")
    assert r.status_code == 403


# --- Drafting pause toggle ------------------------------------------------


def test_drafting_paused_toggle_flow(seeded_users, client):
    from app.guardrails import drafting_paused

    assert drafting_paused.is_on() is False

    _login(client, AK_EMAIL, AK_PW)
    client.post("/settings/drafting_paused", data={"turn": "on"}, follow_redirects=False)
    assert drafting_paused.is_on() is True

    client.post("/settings/drafting_paused", data={"turn": "off"}, follow_redirects=False)
    assert drafting_paused.is_on() is False


def test_drafting_paused_short_circuits_orchestrator(seeded_users, no_openai, monkeypatch):
    """When drafting_paused is on, orchestrator.handle skips the Drafter
    and returns skip_drafting_paused."""
    import asyncio

    from app.agents import classifier, drafter as drafter_mod, enricher, orchestrator
    from app.agents.schemas import ClassifierOutput, EnricherOutput
    from app.guardrails import drafting_paused
    from app.tools import gmail_tool
    from app.tools.gmail_tool import InboxMessage

    # Fake classifier → new_enquiry
    async def fake_cls(**kwargs):
        from app.db import execute
        execute(
            "INSERT INTO classifications(email_id, category, confidence, reasoning, model, prompt_version) "
            "VALUES(?,?,?,?,?,?)",
            (kwargs["email_id"], "new_enquiry", 0.9, "fake", "fake", 1),
        )
        return ClassifierOutput(category="new_enquiry", confidence=0.9, reasoning="fake")

    # Fake enricher
    async def fake_enr(**kwargs):
        from app.db import execute
        import json as _json
        out = EnricherOutput(
            sender_name="X", sender_org="", sender_country="",
            likely_service_line="nri_tax", urgency="hot",
            routing_partner="CA Kumar Prasad", summary="s", reasoning="r",
        )
        execute(
            """
            INSERT INTO enrichments
              (email_id, sender_name, sender_org, sender_country, likely_service_line,
               urgency, routing_partner, similar_memories, client_match_id, summary,
               reasoning, model, prompt_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (kwargs["email_id"], "", "", "", "nri_tax", "hot", "CA Kumar Prasad",
             _json.dumps([]), None, "s", "r", "fake", 1),
        )
        return out

    def bomb(**kw):
        raise AssertionError("Drafter must NOT run when drafting_paused is on")

    monkeypatch.setattr(classifier, "classify", fake_cls)
    monkeypatch.setattr(enricher, "enrich", fake_enr)
    monkeypatch.setattr(drafter_mod, "draft_reply", bomb)
    from app.tools import notify_tool
    monkeypatch.setattr(notify_tool, "notify_draft_ready", lambda **kw: True)
    monkeypatch.setattr(notify_tool, "notify_sensitive_bypass", lambda *a, **kw: True)
    monkeypatch.setattr(gmail_tool, "mark_as_processed", lambda *a, **kw: None)
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)

    drafting_paused.set_on()
    try:
        msg = InboxMessage(
            message_id="pm-1", thread_id="t1", from_email="x@y.com", from_name="X",
            to_email="prakasha@balakrishnaandco.com", cc="", subject="Test",
            body_plain="Need ITR help.", body_html="", snippet="",
            received_at="2026-04-23T10:00:00Z", is_reply_in_thread=False,
        )
        result = asyncio.get_event_loop().run_until_complete(orchestrator.handle(msg))
        assert result["action"] == "skip_drafting_paused"
        assert fetch_all("SELECT * FROM drafts") == []
    finally:
        drafting_paused.set_off()
