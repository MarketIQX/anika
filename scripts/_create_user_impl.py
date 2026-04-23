"""Helper invoked by scripts/create_user.ps1.

Reads the password from stdin so it never appears in process arguments.
Usage (from the project root):
    <password-on-stdin> | python scripts/_create_user_impl.py <email> <role>

Exit codes:
    0  success
    2  user already exists / invalid role / validation error
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
    if len(sys.argv) != 3:
        print("usage: _create_user_impl.py <email> <role>", file=sys.stderr)
        return 1
    email = sys.argv[1]
    role = sys.argv[2]
    password = sys.stdin.read().strip()
    if not password:
        print("Empty password on stdin.", file=sys.stderr)
        return 1

    init_db()
    try:
        u = users.create_user(email, password, role)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"User {u.email} ({u.role}) created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
