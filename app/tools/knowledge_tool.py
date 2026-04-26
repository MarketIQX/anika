"""Firm knowledge lookup — read-only access to firm_knowledge, rules, agent_prompts.

These are grounding facts for Anika: firm profile, tone rules, FAQ answers,
and the active prompt version for every agent. Agents call these via the
Agents SDK tool decorator so the LLM can retrieve facts on demand.
"""
from __future__ import annotations

from typing import Any

from app.db import fetch_all, fetch_one


def get_firm_fact(key: str) -> str | None:
    """Return the stored value for a firm_knowledge key, or None.

    Typical keys: 'firm_name', 'office_address', 'signature_block',
    'positioning_statement', 'track_record', etc.
    """
    row = fetch_one("SELECT value FROM firm_knowledge WHERE key = ?", (key,))
    return row["value"] if row else None


def list_firm_facts(category: str | None = None) -> list[dict[str, Any]]:
    """Return all (key, value, category) rows, optionally filtered."""
    if category:
        return fetch_all(
            "SELECT key, value, category FROM firm_knowledge WHERE category = ? ORDER BY key",
            (category,),
        )
    return fetch_all("SELECT key, value, category FROM firm_knowledge ORDER BY category, key")


def get_signature_block() -> str:
    """Return Prakash sir's signature block — the locked canonical sign-off.

    Source of truth: app/config/firm_identity.SIGNATURE_BLOCK (locked in code).
    Previously this read from firm_knowledge.signature_block which created a
    second source of truth that drifted from the locked version. That bug
    caused double-signature stacking on drafts.

    The legacy DB row in firm_knowledge.signature_block is now ignored.
    """
    from app.config.firm_identity import SIGNATURE_BLOCK
    return SIGNATURE_BLOCK



def get_tone_rules() -> dict[str, list[str]]:
    """Return active do's and don'ts as two lists.

    Shape: {"dos": ["..."], "donts": ["..."]}
    """
    dos = [r["text_value"] for r in fetch_all(
        "SELECT text_value FROM rules WHERE rule_type='tone_do' AND is_active=1"
    )]
    donts = [r["text_value"] for r in fetch_all(
        "SELECT text_value FROM rules WHERE rule_type='tone_dont' AND is_active=1"
    )]
    return {"dos": dos, "donts": donts}


def get_faq_answers() -> list[dict[str, str]]:
    """Return verbatim FAQ answers the Drafter should reuse when applicable."""
    return [
        {"pattern": r["pattern"] or "", "answer": r["text_value"] or ""}
        for r in fetch_all(
            "SELECT pattern, text_value FROM rules WHERE rule_type='faq' AND is_active=1"
        )
    ]


def get_routing_matrix() -> list[dict[str, str]]:
    """Return the service → partner routing matrix."""
    return fetch_all(
        "SELECT key, value FROM firm_knowledge WHERE category='routing' ORDER BY key"
    )


def get_active_prompt(agent_name: str) -> dict[str, Any] | None:
    """Return {id, version, prompt_text} for the active prompt of this agent."""
    return fetch_one(
        """
        SELECT id, version, prompt_text, change_note
        FROM agent_prompts
        WHERE agent_name = ? AND is_active = 1
        ORDER BY version DESC
        LIMIT 1
        """,
        (agent_name,),
    )


def get_blacklist_patterns() -> list[str]:
    """Return active blacklist patterns (sensitive-topic regexes/substrings)."""
    return [r["pattern"] for r in fetch_all(
        "SELECT pattern FROM rules WHERE rule_type='blacklist_topic' AND is_active=1 AND pattern IS NOT NULL"
    )]


def get_rupee_threshold() -> float | None:
    """Return the largest active rupee threshold above which Anika bypasses."""
    row = fetch_one(
        """
        SELECT MAX(threshold_value) AS t FROM rules
        WHERE rule_type='rupee_threshold' AND is_active=1
        """
    )
    return row["t"] if row and row["t"] is not None else None
