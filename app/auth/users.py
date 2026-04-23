"""User-row CRUD and current-user loading.

Thin layer over the `users` table. Keeps the rest of auth free from SQL.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.passwords import hash_password, verify_password
from app.db import execute, fetch_all, fetch_one


@dataclass
class User:
    """In-memory user. Never carries the password hash into templates/logs."""

    id: int
    email: str
    role: str        # 'admin' or 'user'
    created_at: str
    last_login_at: str | None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "User":
        return cls(
            id=int(row["id"]),
            email=row["email"],
            role=row["role"],
            created_at=row["created_at"],
            last_login_at=row.get("last_login_at"),
        )


def get_by_email(email: str) -> User | None:
    """Look up a user by email (case-insensitive). Returns None if missing."""
    row = fetch_one(
        "SELECT id, email, role, created_at, last_login_at FROM users WHERE lower(email)=lower(?)",
        (email,),
    )
    return User.from_row(row) if row else None


def get_password_hash(email: str) -> str | None:
    row = fetch_one(
        "SELECT password_hash FROM users WHERE lower(email)=lower(?)",
        (email,),
    )
    return row["password_hash"] if row else None


def list_users() -> list[User]:
    rows = fetch_all(
        "SELECT id, email, role, created_at, last_login_at FROM users ORDER BY role DESC, email"
    )
    return [User.from_row(r) for r in rows]


def create_user(email: str, password: str, role: str) -> User:
    """Create a user. Raises if email exists or role is invalid."""
    if role not in ("admin", "user"):
        raise ValueError(f"invalid role: {role!r}")
    if get_by_email(email):
        raise ValueError(f"user already exists: {email}")
    pw_hash = hash_password(password)
    execute(
        "INSERT INTO users(email, password_hash, role) VALUES(?,?,?)",
        (email.strip().lower(), pw_hash, role),
    )
    u = get_by_email(email)
    assert u is not None
    return u


def set_password(email: str, new_password: str) -> bool:
    """Update the password hash for an existing user. Returns False if missing."""
    if not get_by_email(email):
        return False
    pw_hash = hash_password(new_password)
    execute(
        "UPDATE users SET password_hash=? WHERE lower(email)=lower(?)",
        (pw_hash, email),
    )
    return True


def touch_last_login(email: str) -> None:
    execute(
        "UPDATE users SET last_login_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE lower(email)=lower(?)",
        (email,),
    )


def authenticate(email: str, password: str) -> User | None:
    """Return the User if credentials match, else None.

    Constant-time-ish: we always run verify_password even when the email is
    unknown, using a sentinel hash, so the timing signal between "wrong email"
    and "wrong password" is minimized.
    """
    # Bogus hash for timing-equalization when user not found. We intentionally
    # always run one verify_password call.
    _DUMMY = "$2b$12$CfW1H4/qJ0lP8x1X2u3WAuZ0wZfQxV3qw8mR9H8qVdLpVkZ1.dDbe"
    stored = get_password_hash(email)
    candidate = stored or _DUMMY
    ok = verify_password(password, candidate)
    if ok and stored is not None:
        return get_by_email(email)
    return None
