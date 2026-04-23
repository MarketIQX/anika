"""Password policy — rules + a single `validate_new_password()` entry point.

Keeps the validation rules out of the route file so tests can hit them
directly and so we can tune the policy in one place.
"""
from __future__ import annotations

MIN_LENGTH = 10


def validate_new_password(
    current: str,
    new_pw: str,
    confirm: str,
) -> list[str]:
    """Return a list of human-readable error messages. Empty list == valid.

    Rules:
      1. New password must be at least MIN_LENGTH characters.
      2. Must contain at least one letter AND at least one digit.
      3. Confirm field must match new_pw exactly.
      4. New must not equal the current password (they'd be pointless).
    """
    errors: list[str] = []

    if len(new_pw) < MIN_LENGTH:
        errors.append(f"New password must be at least {MIN_LENGTH} characters.")

    has_letter = any(c.isalpha() for c in new_pw)
    has_digit = any(c.isdigit() for c in new_pw)
    if not has_letter:
        errors.append("New password must contain at least one letter.")
    if not has_digit:
        errors.append("New password must contain at least one digit.")

    if new_pw != confirm:
        errors.append("New password and confirmation do not match.")

    # Only check "same as current" if it's not already empty and the other
    # errors don't rule it out — avoids piling redundant messages.
    if current and new_pw and new_pw == current:
        errors.append("New password must be different from the current one.")

    return errors
