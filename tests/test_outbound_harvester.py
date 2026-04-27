"""Tests for Phase 1C-3 outbound harvester job.

Mocks gmail_tool.get_thread to inject synthetic thread message lists,
mocks gmail_tool.has_credentials to return True without an OAuth token,
mocks memory_tool.embed deterministically (so voice_harvester downstream
doesn't try to call OpenAI).

Coverage:
  1. happy path — partner outbound found, harvested, draft flipped, row marked
  2. no outbound — no save, no row mark, counter increments
  3. idempotency — already-marked row is not picked up
  4. lookback window — emails older than 7 days are not picked up
  5. short body — counter increments, row marked anyway (don't refetch)
  6. multiple outbounds in thread — only the FIRST one (after received_at) wins
  7. Gmail API error — counter increments, no crash
  8. no_credentials short-circuit
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import random
from datetime import datetime, timedelta, timezone

import pytest
from googleapiclient.errors import HttpError

from app.db import EMBEDDING_DIM, execute, fetch_all, fetch_one
from app.jobs import outbound_harvester
from app.jobs.outbound_harvester import harvest_outbound_replies
from app.tools import gmail_tool, memory_tool
from app.tools.gmail_tool import InboxMessage


# --- Deterministic embed fake (same shape as test_voice_harvester) -------


def _fake_embed(text: str) -> list[float]:
    text = (text or "").strip()
    if not text:
        return []
    h = hashlib.sha256(text.encode("utf-8")).digest()
    rng = random.Random(h)
    v = [rng.gauss(0.0, 1.0) for _ in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v


@pytest.fixture(autouse=True)
def _patch_gmail_and_embed(monkeypatch):
    """Default fixtures every test inherits.

    - has_credentials -> True (so the harvester proceeds)
    - get_thread -> raises NotImplementedError unless a test overrides it
    - memory_tool.embed -> deterministic fake
    """
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: True)
    monkeypatch.setattr(memory_tool, "embed", _fake_embed)

    def _default_get_thread(thread_id):
        raise NotImplementedError(
            "Test forgot to override gmail_tool.get_thread for this case"
        )
    monkeypatch.setattr(gmail_tool, "get_thread", _default_get_thread)
    return monkeypatch


# --- Helpers -------------------------------------------------------------


PRAKASHA = "prakasha@balakrishnaandco.com"
ENQUIRER = "vijay@example.com"


def _ts(offset_seconds: int = 0) -> str:
    """ISO-8601 UTC timestamp now + offset, in Anika's stored format."""
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )


def _seed_email(*, message_id: str, thread_id: str, received_at: str,
                from_email: str = ENQUIRER) -> int:
    cur = execute(
        """
        INSERT INTO raw_emails(gmail_message_id, gmail_thread_id, from_email,
                               to_email, subject, body_plain, received_at)
        VALUES (?,?,?,?,?,?,?)
        """,
        (message_id, thread_id, from_email, PRAKASHA,
         "Tax enquiry", "Original enquiry body", received_at),
    )
    return int(cur.lastrowid)


def _seed_enrichment(email_id: int, service_line: str = "nri_tax") -> None:
    execute(
        """
        INSERT INTO enrichments(email_id, likely_service_line, urgency,
                                routing_partner, summary, reasoning, model)
        VALUES(?,?,?,?,?,?,?)
        """,
        (email_id, service_line, "warm", "CA Kumar Prasad", "summary", "r", "fake"),
    )


def _seed_pending_draft(email_id: int) -> int:
    cur = execute(
        """
        INSERT INTO drafts(email_id, subject, body, model, sent_status)
        VALUES(?, 'Re: enquiry', 'Anika draft body that the partner never saw', 'gpt-4o', 'pending_approval')
        """,
        (email_id,),
    )
    return int(cur.lastrowid)


def _msg(*, message_id: str, thread_id: str, from_email: str, body: str,
         received_at: str) -> InboxMessage:
    """Construct an InboxMessage as the Gmail tool would emit one."""
    return InboxMessage(
        message_id=message_id,
        thread_id=thread_id,
        from_email=from_email.lower(),
        from_name="",
        to_email="",
        cc="",
        subject="Re: Tax enquiry",
        body_plain=body,
        body_html="",
        snippet=body[:80],
        received_at=received_at,
        is_reply_in_thread=True,
    )


PARTNER_BODY = (
    "Dear Vijay, thank you for reaching out. We will be glad to assist with "
    "planning your NRI ITR filing — happy to share fee structure on a quick call."
)


def _run() -> dict[str, int]:
    return asyncio.get_event_loop().run_until_complete(harvest_outbound_replies())


# --- Tests ----------------------------------------------------------------


def test_happy_path_partner_outbound_harvested(monkeypatch):
    """Partner replied directly via Gmail. Harvester saves the body, flips the draft."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-orig", thread_id="t-1", received_at=enquiry_ts)
    _seed_enrichment(eid, "nri_tax")
    draft_id = _seed_pending_draft(eid)

    partner_msg = _msg(
        message_id="gmail-partner-reply",
        thread_id="t-1",
        from_email=PRAKASHA,
        body=PARTNER_BODY,
        received_at=_ts(60),
    )
    enquiry_msg = _msg(
        message_id="m-orig",
        thread_id="t-1",
        from_email=ENQUIRER,
        body="Original enquiry body",
        received_at=enquiry_ts,
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [enquiry_msg, partner_msg])

    counters = _run()
    assert counters["harvested"] == 1
    assert counters["errors"] == 0

    row = fetch_one("SELECT outbound_reply_gmail_id, outbound_reply_harvested_at FROM raw_emails WHERE id=?", (eid,))
    assert row["outbound_reply_gmail_id"] == "gmail-partner-reply"
    assert row["outbound_reply_harvested_at"] is not None

    drow = fetch_one("SELECT sent_status FROM drafts WHERE id=?", (draft_id,))
    assert drow["sent_status"] == "rejected_partner_replied_outside"

    voice = fetch_all(
        "SELECT id, harvest_source, service_line FROM knowledge_library "
        "WHERE is_active=1 AND purpose='voice_example'"
    )
    assert len(voice) == 1
    assert voice[0]["harvest_source"] == "gmail_outbound"
    assert voice[0]["service_line"] == "nri_tax"


def test_thread_with_no_partner_outbound_no_save(monkeypatch):
    """Thread has only the original enquiry — no harvest, but
    outbound_last_scanned_at IS bumped (so next cycle respects backoff
    instead of immediately rescanning)."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-orig", thread_id="t-2", received_at=enquiry_ts)
    enquiry_msg = _msg(
        message_id="m-orig",
        thread_id="t-2",
        from_email=ENQUIRER,
        body="Original enquiry only",
        received_at=enquiry_ts,
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [enquiry_msg])

    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_no_outbound"] == 1

    row = fetch_one(
        "SELECT outbound_reply_gmail_id, outbound_last_scanned_at "
        "FROM raw_emails WHERE id=?", (eid,)
    )
    assert row["outbound_reply_gmail_id"] is None
    assert row["outbound_last_scanned_at"] is not None  # backoff guard set

    voice = fetch_all("SELECT id FROM knowledge_library WHERE purpose='voice_example'")
    assert len(voice) == 0


def test_already_harvested_row_not_picked_up(monkeypatch):
    """Once outbound_reply_gmail_id is set, the row is never rescanned."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-orig", thread_id="t-3", received_at=enquiry_ts)
    execute(
        "UPDATE raw_emails SET outbound_reply_gmail_id='already-marked' WHERE id=?",
        (eid,),
    )
    # If get_thread is invoked, the default mock raises — so the assertion below
    # passes only if the row was correctly skipped at the SQL filter.
    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_no_outbound"] == 0
    assert counters["errors"] == 0


def test_old_email_outside_lookback_window_not_picked_up(monkeypatch):
    """Emails older than HARVEST_LOOKBACK_DAYS are out of scope."""
    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )
    eid = _seed_email(message_id="m-old", thread_id="t-4", received_at=old_ts)
    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_no_outbound"] == 0  # row never reached the loop
    row = fetch_one("SELECT outbound_reply_gmail_id FROM raw_emails WHERE id=?", (eid,))
    assert row["outbound_reply_gmail_id"] is None


def test_short_partner_body_counted_and_row_marked(monkeypatch):
    """Short partner reply ('thanks, noted'): counter increments, row still marked
    so we don't re-fetch the thread next cycle."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-orig", thread_id="t-5", received_at=enquiry_ts)
    short_msg = _msg(
        message_id="gmail-short-reply",
        thread_id="t-5",
        from_email=PRAKASHA,
        body="Thanks.",
        received_at=_ts(60),
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [short_msg])

    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_too_short"] == 1
    row = fetch_one("SELECT outbound_reply_gmail_id FROM raw_emails WHERE id=?", (eid,))
    assert row["outbound_reply_gmail_id"] == "gmail-short-reply"


def test_first_partner_outbound_wins_when_multiple(monkeypatch):
    """If the partner replied twice in the thread, only the first qualifying
    message (earliest after received_at) is harvested."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-orig", thread_id="t-6", received_at=enquiry_ts)

    first = _msg(
        message_id="gmail-first",
        thread_id="t-6",
        from_email=PRAKASHA,
        body=PARTNER_BODY,
        received_at=_ts(30),
    )
    second = _msg(
        message_id="gmail-second",
        thread_id="t-6",
        from_email=PRAKASHA,
        body=PARTNER_BODY + " Follow-up content goes here as well.",
        received_at=_ts(60),
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [first, second])

    counters = _run()
    assert counters["harvested"] == 1
    row = fetch_one("SELECT outbound_reply_gmail_id FROM raw_emails WHERE id=?", (eid,))
    assert row["outbound_reply_gmail_id"] == "gmail-first"


def test_gmail_api_error_increments_counter_no_crash(monkeypatch):
    """HttpError on get_thread is caught; loop continues across other rows."""
    enquiry_ts = _ts(0)
    eid_bad = _seed_email(message_id="m-bad", thread_id="t-bad", received_at=enquiry_ts)
    eid_ok = _seed_email(message_id="m-ok", thread_id="t-ok", received_at=_ts(1))
    _seed_enrichment(eid_ok)

    partner_msg = _msg(
        message_id="gmail-ok-reply",
        thread_id="t-ok",
        from_email=PRAKASHA,
        body=PARTNER_BODY,
        received_at=_ts(60),
    )

    def _flaky_get_thread(thread_id):
        if thread_id == "t-bad":
            raise HttpError(resp=type("R", (), {"status": 500, "reason": "boom"})(), content=b"err")
        return [partner_msg]

    monkeypatch.setattr(gmail_tool, "get_thread", _flaky_get_thread)

    counters = _run()
    assert counters["errors"] == 1
    assert counters["harvested"] == 1  # the OK one still goes through

    bad = fetch_one(
        "SELECT outbound_reply_gmail_id, outbound_last_scanned_at "
        "FROM raw_emails WHERE id=?", (eid_bad,)
    )
    ok = fetch_one(
        "SELECT outbound_reply_gmail_id, outbound_last_scanned_at "
        "FROM raw_emails WHERE id=?", (eid_ok,)
    )
    # Bad row: not harvested (so outbound_reply_gmail_id stays NULL) BUT
    # last_scanned_at is bumped — next cycle respects backoff, no thrash.
    assert bad["outbound_reply_gmail_id"] is None
    assert bad["outbound_last_scanned_at"] is not None
    # Ok row: harvested normally, both columns set.
    assert ok["outbound_reply_gmail_id"] == "gmail-ok-reply"
    assert ok["outbound_last_scanned_at"] is not None


def test_no_credentials_short_circuits(monkeypatch):
    """Without OAuth credentials the harvester returns immediately."""
    monkeypatch.setattr(gmail_tool, "has_credentials", lambda: False)
    counters = _run()
    assert counters.get("no_credentials") == 1
    assert counters["harvested"] == 0


def test_partner_message_at_or_before_received_at_ignored(monkeypatch):
    """If a 'partner' message in the thread is at-or-before the original
    received_at (e.g., the web-form mailer self-sent the enquiry itself),
    it's not a real outbound — must not be harvested."""
    enquiry_ts = _ts(0)
    eid = _seed_email(
        message_id="m-orig",
        thread_id="t-7",
        received_at=enquiry_ts,
        from_email=PRAKASHA,  # self-sent web form
    )
    self_sent = _msg(
        message_id="gmail-self-sent",
        thread_id="t-7",
        from_email=PRAKASHA,
        body="Original web-form notification body that should NOT be harvested.",
        received_at=enquiry_ts,  # exactly equal to received_at
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [self_sent])

    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_no_outbound"] == 1


# --- Backoff scan logic (1C-3 fix) ---------------------------------------
#
# After every scan attempt, outbound_last_scanned_at is bumped. The SQL
# filter skips rows scanned within an age-based backoff window. Each
# of these tests pins one cell of the curve so a future edit that
# loosens or breaks it fails loudly.


def _set_last_scanned(eid: int, ts: str) -> None:
    """Helper: simulate a prior scan at `ts` ISO timestamp."""
    execute(
        "UPDATE raw_emails SET outbound_last_scanned_at=? WHERE id=?",
        (ts, eid),
    )


def test_backoff_skips_recent_email_just_scanned(monkeypatch):
    """A <1hr-old email scanned 1 minute ago is skipped (5 min window for
    fresh enquiries). The row is excluded by the SQL filter, not the
    Python loop — get_thread is never invoked."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-back-1", thread_id="t-back-1", received_at=enquiry_ts)
    one_min_ago = _ts(-60)
    _set_last_scanned(eid, one_min_ago)
    # Default mock raises NotImplementedError on get_thread call; if the
    # filter fails to skip, the test crashes with that.
    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_no_outbound"] == 0  # not even seen
    assert counters["errors"] == 0
    row = fetch_one(
        "SELECT outbound_last_scanned_at FROM raw_emails WHERE id=?", (eid,)
    )
    # Unchanged because the row was never visited.
    assert row["outbound_last_scanned_at"] == one_min_ago


def test_backoff_picks_up_recent_email_after_5min_window(monkeypatch):
    """A <1hr-old email scanned 6 minutes ago IS rescanned (>5 min window)."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-back-2", thread_id="t-back-2", received_at=enquiry_ts)
    six_min_ago = _ts(-360)
    _set_last_scanned(eid, six_min_ago)
    enquiry_msg = _msg(
        message_id="m-back-2", thread_id="t-back-2",
        from_email=ENQUIRER, body="just the original",
        received_at=enquiry_ts,
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [enquiry_msg])

    counters = _run()
    assert counters["skipped_no_outbound"] == 1  # was scanned this cycle
    row = fetch_one(
        "SELECT outbound_last_scanned_at FROM raw_emails WHERE id=?", (eid,)
    )
    # Bumped to a more recent timestamp.
    assert row["outbound_last_scanned_at"] != six_min_ago


def test_backoff_old_email_uses_long_window(monkeypatch):
    """A 2-day-old email scanned 4 hours ago IS skipped — the ≥1d age
    bucket uses a 1-day rescan window, so 4 hours isn't enough."""
    two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )
    eid = _seed_email(
        message_id="m-back-3", thread_id="t-back-3", received_at=two_days_ago
    )
    four_hr_ago = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime(
        "%Y-%m-%dT%H:%M:%fZ"
    )
    _set_last_scanned(eid, four_hr_ago)
    counters = _run()
    assert counters["harvested"] == 0
    assert counters["skipped_no_outbound"] == 0  # excluded by SQL filter
    assert counters["errors"] == 0


def test_first_scan_picks_up_never_scanned_row(monkeypatch):
    """A row with outbound_last_scanned_at IS NULL is always eligible —
    backoff has no effect on the first scan."""
    enquiry_ts = _ts(0)
    eid = _seed_email(message_id="m-back-4", thread_id="t-back-4", received_at=enquiry_ts)
    # Confirm starting state.
    pre = fetch_one(
        "SELECT outbound_last_scanned_at FROM raw_emails WHERE id=?", (eid,)
    )
    assert pre["outbound_last_scanned_at"] is None

    enquiry_msg = _msg(
        message_id="m-back-4", thread_id="t-back-4",
        from_email=ENQUIRER, body="orig", received_at=enquiry_ts,
    )
    monkeypatch.setattr(gmail_tool, "get_thread", lambda tid: [enquiry_msg])
    counters = _run()
    assert counters["skipped_no_outbound"] == 1
    post = fetch_one(
        "SELECT outbound_last_scanned_at FROM raw_emails WHERE id=?", (eid,)
    )
    assert post["outbound_last_scanned_at"] is not None


def test_last_scanned_at_bumped_even_on_gmail_error(monkeypatch):
    """When get_thread raises HttpError, last_scanned_at is still bumped —
    no thrash on persistently-broken threads. Backoff window applies
    independent of outcome."""
    enquiry_ts = _ts(0)
    eid = _seed_email(
        message_id="m-back-5", thread_id="t-back-5", received_at=enquiry_ts
    )

    def _raises(thread_id):
        raise HttpError(
            resp=type("R", (), {"status": 500, "reason": "boom"})(),
            content=b"err",
        )
    monkeypatch.setattr(gmail_tool, "get_thread", _raises)

    counters = _run()
    assert counters["errors"] == 1
    row = fetch_one(
        "SELECT outbound_last_scanned_at FROM raw_emails WHERE id=?", (eid,)
    )
    assert row["outbound_last_scanned_at"] is not None
