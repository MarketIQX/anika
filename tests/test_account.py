"""Tests for /account — self-service password change."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth import users as users_mod
from app.auth.password_policy import validate_new_password
from app.db import fetch_one


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


def _login(client: TestClient, email: str, password: str) -> None:
    r = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    assert r.status_code == 303, f"login failed: {r.status_code} {r.text}"


# --- Policy unit tests (no HTTP) -------------------------------------------


def test_policy_accepts_strong_password():
    assert validate_new_password("oldpw", "abcdef1234", "abcdef1234") == []


def test_policy_rejects_short_password():
    errs = validate_new_password("old", "abc123", "abc123")
    assert any("at least 10" in e for e in errs)


def test_policy_rejects_missing_digit():
    errs = validate_new_password("old", "abcdefghij", "abcdefghij")
    assert any("digit" in e for e in errs)


def test_policy_rejects_missing_letter():
    errs = validate_new_password("old", "1234567890", "1234567890")
    assert any("letter" in e for e in errs)


def test_policy_rejects_confirm_mismatch():
    errs = validate_new_password("old", "abcdef1234", "abcdef9999")
    assert any("do not match" in e for e in errs)


def test_policy_rejects_same_as_current():
    errs = validate_new_password("abcdef1234", "abcdef1234", "abcdef1234")
    assert any("different from the current" in e for e in errs)


# --- Route auth ------------------------------------------------------------


def test_account_requires_auth(client):
    r = client.get("/account", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_change_password_post_requires_auth(client):
    r = client.post(
        "/account/change-password",
        data={
            "current_password": "x",
            "new_password": "y",
            "confirm_password": "y",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_account_page_renders_for_authed_user(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.get("/account")
    assert r.status_code == 200
    assert b"Change password" in r.content
    assert AK_EMAIL.encode() in r.content


# --- Happy path ------------------------------------------------------------


def test_successful_password_change(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    new_pw = "BrandNewPass-2026"
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": new_pw,
            "confirm_password": new_pw,
        },
    )
    assert r.status_code == 200
    assert b"Password updated" in r.content

    # New password works, old does not.
    assert users_mod.authenticate(AK_EMAIL, new_pw) is not None
    assert users_mod.authenticate(AK_EMAIL, AK_PW) is None

    # access_log row landed.
    row = fetch_one(
        "SELECT * FROM access_log WHERE action='password_changed' AND user_email=?",
        (AK_EMAIL,),
    )
    assert row is not None


def test_session_stays_active_after_password_change(seeded_users, client):
    """User should not be logged out of their existing session."""
    _login(client, AK_EMAIL, AK_PW)
    new_pw = "AnotherNewPass-9999"
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": new_pw,
            "confirm_password": new_pw,
        },
    )
    assert r.status_code == 200
    # A subsequent protected request should succeed without re-login.
    r2 = client.get("/drafts")
    assert r2.status_code == 200


def test_password_change_works_for_user_role_too(seeded_users, client):
    _login(client, PK_EMAIL, PK_PW)
    new_pw = "PrakashaNew-2026!"
    r = client.post(
        "/account/change-password",
        data={
            "current_password": PK_PW,
            "new_password": new_pw,
            "confirm_password": new_pw,
        },
    )
    assert r.status_code == 200
    assert users_mod.authenticate(PK_EMAIL, new_pw) is not None


# --- Validation failures ---------------------------------------------------


def test_wrong_current_password_rejected(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.post(
        "/account/change-password",
        data={
            "current_password": "totally-wrong",
            "new_password": "StrongNew-2026",
            "confirm_password": "StrongNew-2026",
        },
    )
    assert r.status_code == 400
    assert b"Current password is incorrect" in r.content
    # Original password still works.
    assert users_mod.authenticate(AK_EMAIL, AK_PW) is not None
    # No access_log row for a 'password_changed' on this user.
    row = fetch_one(
        "SELECT * FROM access_log WHERE action='password_changed' AND user_email=?",
        (AK_EMAIL,),
    )
    assert row is None


def test_new_password_too_short_rejected(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": "abc123",
            "confirm_password": "abc123",
        },
    )
    assert r.status_code == 400
    assert b"at least 10" in r.content
    assert users_mod.authenticate(AK_EMAIL, AK_PW) is not None  # unchanged


def test_new_password_missing_digit_rejected(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": "onlylettersfornow",
            "confirm_password": "onlylettersfornow",
        },
    )
    assert r.status_code == 400
    assert b"digit" in r.content


def test_new_password_missing_letter_rejected(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": "1234567890",
            "confirm_password": "1234567890",
        },
    )
    assert r.status_code == 400
    assert b"letter" in r.content


def test_new_password_equals_current_rejected(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": AK_PW,
            "confirm_password": AK_PW,
        },
    )
    assert r.status_code == 400
    assert b"different from the current" in r.content
    assert users_mod.authenticate(AK_EMAIL, AK_PW) is not None


def test_confirm_mismatch_rejected(seeded_users, client):
    _login(client, AK_EMAIL, AK_PW)
    r = client.post(
        "/account/change-password",
        data={
            "current_password": AK_PW,
            "new_password": "NewGoodPass-2026",
            "confirm_password": "NewGoodPass-2027",
        },
    )
    assert r.status_code == 400
    assert b"do not match" in r.content


def test_header_has_change_password_link(seeded_users, client):
    """The base layout should expose a 'Change password' link for authed users."""
    _login(client, AK_EMAIL, AK_PW)
    r = client.get("/drafts")
    assert r.status_code == 200
    assert b"Change password" in r.content
    assert b'href="/account"' in r.content
