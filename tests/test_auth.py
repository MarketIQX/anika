"""Authentication tests — login, logout, route protection, RBAC, audit log."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth import users as users_mod
from app.auth.passwords import hash_password, verify_password
from app.db import fetch_all, fetch_one


AK_EMAIL = "aks@marketiqx.com"
AK_PW = "ak-test-password-1234"
PK_EMAIL = "prakasha@balakrishnaandco.com"
PK_PW = "pk-test-password-5678"


@pytest.fixture
def seeded_users():
    """Create the two canonical users directly (bypasses the random-password path)."""
    users_mod.create_user(AK_EMAIL, AK_PW, role="admin")
    users_mod.create_user(PK_EMAIL, PK_PW, role="user")


@pytest.fixture
def client():
    """TestClient against the real app, with lifespan suppressed.

    Why no `with` / no lifespan: the conftest `isolated_db` fixture already
    initialized the DB. If we let the lifespan run, it would call
    `seed_initial_users()` with the live env vars and collide with tests
    that seed users themselves.
    """
    from app.main import app

    return TestClient(app)


# -------- hashing --------

def test_bcrypt_round_trip():
    h = hash_password("hunter2")
    assert h.startswith("$2b$")
    assert verify_password("hunter2", h) is True
    assert verify_password("wrong", h) is False


def test_authenticate_rejects_unknown_user():
    assert users_mod.authenticate("ghost@x.com", "anything") is None


def test_authenticate_accepts_correct_password(seeded_users):
    u = users_mod.authenticate(AK_EMAIL, AK_PW)
    assert u is not None
    assert u.email == AK_EMAIL
    assert u.role == "admin"


def test_authenticate_rejects_wrong_password(seeded_users):
    assert users_mod.authenticate(AK_EMAIL, "not-it") is None


# -------- login / logout --------

def test_login_page_renders(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert b"Sign in" in r.content


def test_login_success_sets_session_and_logs(seeded_users, client):
    r = client.post(
        "/login",
        data={"email": AK_EMAIL, "password": AK_PW},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/drafts"
    # Session cookie present.
    assert "anika_session" in r.cookies
    # Access log has a login_success row.
    row = fetch_one(
        "SELECT * FROM access_log WHERE action='login_success' AND user_email=?",
        (AK_EMAIL,),
    )
    assert row is not None


def test_login_failure_401_and_audit_row(client):
    r = client.post(
        "/login",
        data={"email": AK_EMAIL, "password": "wrong"},
        follow_redirects=False,
    )
    assert r.status_code == 401
    row = fetch_one(
        "SELECT * FROM access_log WHERE action='login_failure' AND user_email=?",
        (AK_EMAIL.lower(),),
    )
    assert row is not None


def test_logout_clears_session(seeded_users, client):
    client.post("/login", data={"email": AK_EMAIL, "password": AK_PW})
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    # Subsequent protected request should redirect back to /login.
    r2 = client.get("/drafts", follow_redirects=False)
    assert r2.status_code == 303


# -------- route protection --------

def test_unauthenticated_drafts_redirects(client):
    r = client.get("/drafts", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_unauthenticated_settings_redirects(client):
    r = client.get("/settings", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_healthz_is_public(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# -------- role-based access --------

def test_user_role_cannot_access_train(seeded_users, client):
    client.post("/login", data={"email": PK_EMAIL, "password": PK_PW})
    r = client.get("/train", follow_redirects=False)
    assert r.status_code == 403


def test_user_role_cannot_access_analytics(seeded_users, client):
    client.post("/login", data={"email": PK_EMAIL, "password": PK_PW})
    r = client.get("/analytics", follow_redirects=False)
    assert r.status_code == 403


def test_user_role_cannot_access_audit_log(seeded_users, client):
    client.post("/login", data={"email": PK_EMAIL, "password": PK_PW})
    r = client.get("/settings/audit", follow_redirects=False)
    assert r.status_code == 403


def test_user_role_cannot_add_clients(seeded_users, client):
    client.post("/login", data={"email": PK_EMAIL, "password": PK_PW})
    r = client.post(
        "/settings/clients/add",
        data={"email": "x@y.com", "name": "x"},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_admin_can_access_train_and_analytics(seeded_users, client):
    client.post("/login", data={"email": AK_EMAIL, "password": AK_PW})
    assert client.get("/train").status_code == 200
    assert client.get("/analytics").status_code == 200
    assert client.get("/settings/audit").status_code == 200


def test_user_role_can_toggle_kill_switch(seeded_users, client):
    # Both roles are allowed to halt Anika — kill switch is a safety control.
    client.post("/login", data={"email": PK_EMAIL, "password": PK_PW})
    r = client.post(
        "/settings/kill_switch",
        data={"turn": "on"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    row = fetch_one(
        "SELECT * FROM access_log WHERE action='kill_switch_on' AND user_email=?",
        (PK_EMAIL,),
    )
    assert row is not None


# -------- session tamper guard --------

def test_modified_session_cookie_fails_auth(seeded_users, client):
    client.post("/login", data={"email": AK_EMAIL, "password": AK_PW})
    # Tamper the signed session cookie.
    client.cookies.set("anika_session", "obviously-bogus-value")
    r = client.get("/drafts", follow_redirects=False)
    assert r.status_code == 303  # redirected to login
    assert "/login" in r.headers["location"]


# -------- access log append-only --------

def test_access_log_cannot_be_updated_or_deleted():
    import sqlite3
    from app.db import execute as _exe
    from app.auth import access_log

    rid = access_log.log(action="login_success", user_email="x@y.com")
    with pytest.raises(sqlite3.IntegrityError):
        _exe("UPDATE access_log SET action='tampered' WHERE id=?", (rid,))
    with pytest.raises(sqlite3.IntegrityError):
        _exe("DELETE FROM access_log WHERE id=?", (rid,))


# -------- initial bootstrap --------

def test_bootstrap_seeds_both_users_when_table_empty(monkeypatch):
    """Fresh DB + env vars set → both users created; no random passwords returned."""
    from app.auth import bootstrap

    # Conftest fresh DB already gives empty users table.
    # Set env vars via the (shared) test settings instance.
    s = bootstrap.get_settings()
    s.ak_initial_password = "seed-pw-ak"
    s.prakasha_initial_password = "seed-pw-pk"

    result = bootstrap.seed_initial_users()
    # No generated passwords returned when env vars were set.
    assert result["ak"] is None
    assert result["prakasha"] is None
    # Both users now exist with correct roles.
    assert users_mod.authenticate(s.ak_email, "seed-pw-ak") is not None
    assert users_mod.authenticate(s.prakasha_email, "seed-pw-pk") is not None


def test_bootstrap_generates_random_passwords_when_env_blank():
    from app.auth import bootstrap

    s = bootstrap.get_settings()
    s.ak_initial_password = ""
    s.prakasha_initial_password = ""

    result = bootstrap.seed_initial_users()
    assert result["ak"] is not None
    assert result["prakasha"] is not None
    # Generated passwords are ≥ 16 chars.
    assert len(result["ak"]["password"]) >= 16
    # And they actually work.
    assert users_mod.authenticate(result["ak"]["email"], result["ak"]["password"]) is not None


def test_bootstrap_is_idempotent(seeded_users):
    """If users already exist, bootstrap is a no-op."""
    from app.auth import bootstrap

    before = fetch_all("SELECT password_hash FROM users")
    result = bootstrap.seed_initial_users()
    after = fetch_all("SELECT password_hash FROM users")
    assert before == after  # password hashes unchanged
    assert result == {"ak": None, "prakasha": None}


# -------- security headers --------

def test_security_headers_present(client):
    r = client.get("/login")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
    assert r.headers.get("Referrer-Policy")
