"""Password hashing with bcrypt.

Why bcrypt: adaptive work factor, battle-tested, the ICAI profession appreciates
defensible choices. We use cost=12 — ~250ms per verify on modern hardware, fine
for the dashboard's single-user-at-a-time load.

Why not passlib: bcrypt is a thinner dependency, maintained, and the API we need
is two functions.
"""
from __future__ import annotations

import secrets
import string

import bcrypt

# Cost factor. 12 is the current industry default (mid-2020s) — tune up as
# hardware improves. Each +1 doubles verify time.
BCRYPT_COST = 12


def hash_password(plain: str) -> str:
    """Return a bcrypt hash string for storage in users.password_hash.

    Raises ValueError on empty input — we never want to accidentally hash "".
    """
    if not plain:
        raise ValueError("password must not be empty")
    salt = bcrypt.gensalt(rounds=BCRYPT_COST)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, stored_hash: str) -> bool:
    """Return True iff `plain` matches `stored_hash`. Constant-time comparison."""
    if not plain or not stored_hash:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash in DB — log elsewhere, refuse the login.
        return False


def generate_random_password(length: int = 20) -> str:
    """Generate a URL-safe random password for auto-seeded users.

    Uses ASCII letters + digits + a few special chars. Length 20 gives
    ≈ 118 bits of entropy — comfortable for a human-initial password.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-+"
    return "".join(secrets.choice(alphabet) for _ in range(length))
