"""Helper invoked by scripts/set_password.ps1.

Reads the new password from stdin so it never appears in process arguments.
Usage (from the project root):
    <password-on-stdin> | python scripts/_set_password_impl.py <email>

Exit codes:
    0  success
    2  no user with that email
    3  update failed (shouldn't happen unless the DB is corrupt)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (parent of scripts/) is on sys.path so `import app`
# works when this file is invoked directly by PowerShell.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import users  # noqa: E402
from app.db import init_db  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: _set_password_impl.py <email>", file=sys.stderr)
        return 1
    email = sys.argv[1]
    password = sys.stdin.read().strip()
    if not password:
        print("Empty password on stdin.", file=sys.stderr)
        return 1

    init_db()
    if not users.get_by_email(email):
        print(f"No user with email: {email}", file=sys.stderr)
        return 2
    if not users.set_password(email, password):
        print("Update failed.", file=sys.stderr)
        return 3
    print(f"Password updated for {email}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
