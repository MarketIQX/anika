"""First-boot user seeding.

If the `users` table is empty, create:
  - AK          (role=admin)  from AK_EMAIL + AK_INITIAL_PASSWORD
  - Prakash sir (role=user)   from PRAKASHA_EMAIL + PRAKASHA_INITIAL_PASSWORD

If either password env var is empty, a random password is generated and
printed ONCE to the console with a loud warning. Subsequent boots do nothing.
"""
from __future__ import annotations

import logging

from app.auth import users
from app.auth.passwords import generate_random_password
from app.config import get_settings
from app.db import fetch_one

logger = logging.getLogger(__name__)


def _banner(line: str) -> None:
    """Print a visible banner to stdout for one-time-initial-password display."""
    bar = "!" * 78
    print(bar, flush=True)
    print(f"! {line}", flush=True)
    print(bar, flush=True)


def seed_initial_users() -> dict[str, dict[str, str] | None]:
    """Ensure AK + Prakash sir exist as users. Returns a map with any generated passwords.

    Shape: {"created": {"email": ..., "password": ...} | None, ...}
    Password values are only populated when we had to generate a random one
    (i.e., the env var was blank). Existing users are left untouched.
    """
    s = get_settings()
    result: dict[str, dict[str, str] | None] = {"ak": None, "prakasha": None}

    # Only run the initial-seed path if users table is empty. If someone has
    # already created a user manually via the CLI script, don't override.
    row = fetch_one("SELECT COUNT(*) AS n FROM users")
    if row and int(row["n"]) > 0:
        return result

    # AK (admin)
    ak_pw = s.ak_initial_password.strip()
    ak_was_generated = False
    if not ak_pw:
        ak_pw = generate_random_password()
        ak_was_generated = True
    try:
        users.create_user(s.ak_email, ak_pw, role="admin")
        if ak_was_generated:
            result["ak"] = {"email": s.ak_email, "password": ak_pw}
    except ValueError as e:
        logger.warning("Could not seed AK user: %s", e)

    # Prakash sir (user)
    pk_pw = s.prakasha_initial_password.strip()
    pk_was_generated = False
    if not pk_pw:
        pk_pw = generate_random_password()
        pk_was_generated = True
    try:
        users.create_user(s.prakasha_email, pk_pw, role="user")
        if pk_was_generated:
            result["prakasha"] = {"email": s.prakasha_email, "password": pk_pw}
    except ValueError as e:
        logger.warning("Could not seed Prakash sir user: %s", e)

    # Loud console banner for any generated passwords — this is the ONLY time
    # they appear anywhere, by design.
    if result["ak"] or result["prakasha"]:
        _banner("INITIAL PASSWORDS (save these now, they will not be shown again)")
        if result["ak"]:
            print(f"  admin : {result['ak']['email']}  =>  {result['ak']['password']}", flush=True)
        if result["prakasha"]:
            print(f"  user  : {result['prakasha']['email']}  =>  {result['prakasha']['password']}", flush=True)
        _banner("Change them at once via scripts\\set_password.ps1 or the login form.")

    return result
