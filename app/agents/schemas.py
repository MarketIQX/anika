"""Pydantic models — structured outputs for every agent.

Using structured outputs (Agents SDK `output_type`) makes each agent's
decisions machine-readable and writable to the database without brittle
string parsing.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------- Classifier ----------


Category = Literal[
    "new_enquiry",
    "existing_client",
    "sensitive",
    "recruitment_enquiry",
    "vendor_pitch",
    "automated",
    "spam",
    "other",
]


class ClassifierOutput(BaseModel):
    """Classifier output — which of the 5 buckets does this email belong to?"""

    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(
        description="One or two sentences of chain-of-thought justifying the category."
    )


# ---------- Enricher ----------


ServiceLine = Literal[
    "nri_tax",
    "foreign_subsidiary",
    "transfer_pricing",
    "virtual_cfo",
    "gst_indirect",
    "secretarial_roc",
    "audit",
    "other",
]

Urgency = Literal["hot", "warm", "cold"]


class EnricherOutput(BaseModel):
    """Sender intelligence for an enquiry."""

    sender_name: str = Field(description="Display name if identifiable; else empty string.")
    sender_org: str = Field(description="Company/org name if identifiable; else empty string.")
    sender_country: str = Field(description="Best-guess country; else empty string.")
    likely_service_line: ServiceLine
    urgency: Urgency
    routing_partner: str = Field(
        description=(
            "Partner name per the firm's routing matrix (e.g., 'CA Kumar Prasad'). "
            "Empty if uncertain."
        )
    )
    summary: str = Field(description="2-line summary for the approval card.")
    reasoning: str


# ---------- Drafter ----------


class DrafterOutput(BaseModel):
    """Draft reply produced for an enquiry."""

    subject: str = Field(description="Reply subject (usually prefixed with 'Re: ').")
    body: str = Field(
        description=(
            "Plain-text reply body. MUST end with the signature block returned by "
            "the get_signature_block tool."
        )
    )
    tone_notes: str = Field(
        description="One short sentence capturing the voice/formality choices."
    )
    reasoning: str


# ---------- Learner (used via learning_engine, not as an Agents SDK agent) ----------


class LearnerOutput(BaseModel):
    category: Literal["style", "fact", "context", "rejection"]
    rationale: str
    extracted_fact: str | None = None
    style_rule: str | None = None
