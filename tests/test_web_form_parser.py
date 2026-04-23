"""Tests for the website-form parser.

The Chandrika fixture is a real-shape HTML mailer (based on the production
mailer observed in the Balakrishna inbox). Smaller fixtures exercise the
detection and field-extraction rules in isolation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.tools import web_form_parser
from app.tools.web_form_parser import WebFormEnquiry, is_web_form, parse


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def chandrika_html() -> str:
    return (FIXTURES_DIR / "web_form_chandrika.html").read_text(encoding="utf-8")


# --- is_web_form ----------------------------------------------------------


def test_detects_via_mailsub_id(chandrika_html):
    assert is_web_form("", chandrika_html) is True


def test_detects_via_plain_markers():
    plain = (
        "Congratulation! You receive Want to consult us from x@y.com. Details here:\n"
        "Name: X\nEmail: x@y.com\nMessage: Hello"
    )
    assert is_web_form(plain, "") is True


def test_does_not_trigger_on_regular_mail():
    assert is_web_form("Hi, I need NRI tax help.", "<p>Hi there</p>") is False


def test_requires_both_plain_markers():
    # "You receive" alone is not enough
    assert is_web_form("You receive gifts often", "") is False
    # "Details here:" alone is not enough
    assert is_web_form("Details here: please see below", "") is False


# --- parse — the Chandrika happy path -------------------------------------


def test_parses_chandrika_fixture(chandrika_html):
    r = parse("", chandrika_html)
    assert isinstance(r, WebFormEnquiry)
    assert r.sender_email == "chandrika.reddy@example.com"
    assert r.sender_name == "Chandrika Reddy"
    assert r.phone == "+91 98765 43210"
    assert r.ip_address == "103.22.45.67"
    # Message keeps its multi-paragraph shape.
    assert "NRI currently based in Dubai" in r.message
    assert "TDS and capital gains" in r.message
    assert "Regards" in r.message


def test_parses_plain_text_only():
    plain = (
        "Congratulation! You receive Want to consult us from p@q.com. Details here:\n"
        "Name: Priya Menon\n"
        "Phone Number: 9876543210\n"
        "Email: p@q.com\n"
        "IP Address: 1.2.3.4\n"
        "Message: Looking for Virtual CFO support for a seed-stage startup."
    )
    r = parse(plain, "")
    assert r is not None
    assert r.sender_email == "p@q.com"
    assert r.sender_name == "Priya Menon"
    assert r.phone == "9876543210"
    assert r.ip_address == "1.2.3.4"
    assert "Virtual CFO" in r.message


def test_returns_none_for_non_web_form():
    assert parse("Hi, I need help with my GST return.", "") is None
    assert parse("", "<p>A normal HTML email</p>") is None


def test_name_fallback_from_email_local_part_when_missing():
    """No explicit Name: line — derive a pretty name from the email local-part."""
    plain = (
        "Congratulation! You receive Want to consult us from john.doe@example.com. Details here:\n"
        "Email: john.doe@example.com\n"
        "Message: Need help filing."
    )
    r = parse(plain, "")
    assert r is not None
    assert r.sender_email == "john.doe@example.com"
    # "john.doe" → "John Doe"
    assert r.sender_name == "John Doe"


def test_returns_none_when_email_cannot_be_extracted():
    """A 'web-form-shaped' mailer with no discoverable email → None.

    We'd rather the orchestrator treat it as a normal email (probably
    classified 'automated' or 'other') than reply to nobody.
    """
    plain = (
        "Congratulation! You receive a submission. Details here:\n"
        "Name: Anonymous\n"
        "Message: Hello"
    )
    assert parse(plain, "") is None


def test_email_is_lowercased():
    plain = (
        "Congratulation! You receive Want to consult us from John.Doe@EXAMPLE.COM. Details here:\n"
        "Email: John.Doe@EXAMPLE.COM\n"
        "Message: Hi"
    )
    r = parse(plain, "")
    assert r is not None
    assert r.sender_email == "john.doe@example.com"
