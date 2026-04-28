"""Unit tests for the deterministic pre-LLM classifier patterns.

Production gap surfaced by draft 44 (preethinjeevan97@gmail.com,
"Hello Sir, Is there any vacancies in your firm."): the earlier
recruitment patterns required a verb anchor like "looking for ..."
which this natural phrasing skipped, so the email fell through to
the LLM and was misclassified as new_enquiry.

Fix added three patterns covering common recruitment phrasings.
These tests pin each new pattern by the exact production-style text
that should now trigger it.
"""
from __future__ import annotations

from app.agents.classifier import _pre_llm_classify


def test_any_vacancies_in_your_firm_classified_recruitment():
    """The exact phrasing from production draft 44."""
    result = _pre_llm_classify(
        subject="Job enquiry",
        body=(
            "Hello Sir, Is there any vacancies in your firm. I am a "
            "B.Com graduate looking forward to start my career."
        ),
    )
    assert result is not None
    category, reasoning = result
    assert category == "recruitment_enquiry"
    assert "any vacancies" in reasoning.lower() or "vacancy" in reasoning.lower()


def test_position_with_your_firm_classified_recruitment():
    """Direct-ask phrasing: 'looking for a position with your firm'."""
    result = _pre_llm_classify(
        subject="Career opportunity",
        body=(
            "Respected Sir, I am looking for a position with your firm. "
            "I have completed my CA Inter and have 1 year of experience."
        ),
    )
    assert result is not None
    category, _reasoning = result
    assert category == "recruitment_enquiry"


def test_hiring_plus_ca_anchor_classified_recruitment():
    """The 'hiring' verb only fires when paired with a CA-specific
    anchor (CA / CS / articleship / fresher) — prevents false positives
    on unrelated payroll or HR advisory enquiries."""
    result = _pre_llm_classify(
        subject="Hiring enquiry",
        body=(
            "Sir, are you hiring any CA freshers this season? I have "
            "just cleared my CA Final and would love to join."
        ),
    )
    assert result is not None
    category, _reasoning = result
    assert category == "recruitment_enquiry"
