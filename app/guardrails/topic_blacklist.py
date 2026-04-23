"""Sensitive-topic detector — bypass Anika on dangerous enquiries.

Checks three things:
  1. The enquiry body against blacklist_topic patterns (case-insensitive
     substring match — patterns are short phrases like "legal notice").
  2. Any rupee amount mentioned above the configured threshold.
  3. Classifier confidence for 'sensitive' category.

Returns (is_sensitive, reason).
"""
from __future__ import annotations

import re
from typing import Iterable

from app.tools import knowledge_tool

# Matches "Rs 50 lakhs", "Rs. 50L", "₹50,00,000", "INR 5000000", "5 crore"
_AMOUNT_RE = re.compile(
    r"""(?ix)
    (?:
        (?:rs\.?\s*|rupees?\s*|inr\s*|₹\s*)
        (\d[\d,]*\.?\d*)
        (\s*(lakh|lakhs|lac|crore|crores|cr|l|k|m))?
      |
        (\d[\d,]*\.?\d*)
        \s*(lakh|lakhs|lac|crore|crores|cr)\b
    )
    """
)

_UNIT_MULTIPLIERS = {
    "lakh": 100_000,
    "lakhs": 100_000,
    "lac": 100_000,
    "l": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "cr": 10_000_000,
    "k": 1_000,
    "m": 1_000_000,
}


def _largest_rupee_amount(text: str) -> float:
    largest = 0.0
    for match in _AMOUNT_RE.finditer(text or ""):
        num = match.group(1) or match.group(4)
        unit = (match.group(3) or match.group(5) or "").strip().lower()
        try:
            val = float((num or "0").replace(",", ""))
        except ValueError:
            continue
        if unit in _UNIT_MULTIPLIERS:
            val *= _UNIT_MULTIPLIERS[unit]
        largest = max(largest, val)
    return largest


def check(subject: str, body: str) -> tuple[bool, str]:
    """Return (is_sensitive, human-readable reason) for (subject, body)."""
    haystack = f"{subject or ''}\n{body or ''}".lower()

    for pattern in knowledge_tool.get_blacklist_patterns():
        if pattern and pattern.lower() in haystack:
            return True, f"blacklist pattern matched: '{pattern}'"

    threshold = knowledge_tool.get_rupee_threshold()
    if threshold is not None:
        amount = _largest_rupee_amount(haystack)
        if amount > float(threshold):
            return True, f"rupee amount {amount:,.0f} exceeds threshold {threshold:,.0f}"

    return False, ""


def check_text(*texts: Iterable[str]) -> tuple[bool, str]:
    """Variadic helper: check against multiple concatenated blobs."""
    return check("", "\n".join(t or "" for t in texts))
