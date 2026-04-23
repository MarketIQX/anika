"""Tests for the four guardrails."""
from __future__ import annotations

import pytest

from app.guardrails import daily_cap, kill_switch, topic_blacklist, vip_filter
from app.jobs import backfill_memory
from app.tools import client_tool


@pytest.fixture
def seeded_rules():
    backfill_memory._seed_firm_knowledge()
    backfill_memory._seed_rules()


def test_kill_switch_cycle():
    assert kill_switch.is_on() is False
    kill_switch.set_on()
    assert kill_switch.is_on() is True
    kill_switch.set_off()
    assert kill_switch.is_on() is False


def test_blacklist_catches_legal_notice(seeded_rules):
    sensitive, reason = topic_blacklist.check(
        "Legal notice from Income Tax",
        "Dear Sir, I received a legal notice from the Income Tax Department",
    )
    assert sensitive
    assert "legal notice" in reason.lower()


def test_blacklist_rupee_threshold_catches_large_amount(seeded_rules):
    sensitive, reason = topic_blacklist.check(
        "Query",
        "We have a one-time capital gain of Rs 2 crores to plan for",
    )
    assert sensitive
    assert "rupee" in reason.lower()


def test_blacklist_passes_benign_email(seeded_rules):
    sensitive, _ = topic_blacklist.check(
        "NRI ITR filing",
        "Dear Sir, I need help filing my ITR-2 for last year.",
    )
    assert not sensitive


def test_vip_filter_skips_flagged_sender():
    client_tool.upsert_client(
        email="vip@example.com", name="VIP", is_vip_flag=True
    )
    skip, reason = vip_filter.should_skip_draft("vip@example.com")
    assert skip
    assert "vip" in reason.lower()


def test_vip_filter_lets_unknown_through():
    skip, _ = vip_filter.should_skip_draft("random@example.com")
    assert not skip


def test_daily_cap_counts_down():
    # The conftest fixture gives us a shared test_settings instance; mutate
    # its field directly. Pydantic models are mutable by default.
    from app.guardrails import daily_cap as dc

    # daily_cap imports get_settings via from-import; reach the patched one.
    settings = dc.get_settings()
    settings.daily_send_cap = 2

    assert daily_cap.remaining() == 2
    assert daily_cap.try_consume() is True
    assert daily_cap.remaining() == 1
    assert daily_cap.try_consume() is True
    assert daily_cap.try_consume() is False  # cap hit
    assert daily_cap.remaining() == 0
