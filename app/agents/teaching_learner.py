"""Teaching Learner — extracts structured units from uploaded teaching content.

Distinct from `app/agents/learner.py` (which classifies Prakasha sir's EDITS to
drafts). This one reads raw teaching content (pasted text or extracted file
content) and produces:

    LearnerOutput {
        units:          list[Unit]            — the knowledge to add
        clarifications: list[Clarification]   — questions to ask when the
                                                 auto-classification confidence
                                                 is below 0.8
    }

Adaptive clarification limit: max(3, min(10, ceil(num_units * 0.3))).
Extra clarifications (if any) are stored anyway but flagged `priority='low'`
so the UI can fold them under "more clarifications available".

Runs on gpt-4o-mini. Output is a Pydantic structured type.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.cognitive import reasoning_log
from app.config import get_settings

# --- Output schema ---------------------------------------------------------


Kind = Literal["rule", "example", "fact", "policy"]
Scope = Literal["universal", "service_line"]


class LearnerUnit(BaseModel):
    kind: Kind
    content: str = Field(description="The self-contained text of this unit.")
    service_line: str = Field(
        default="",
        description=(
            "Service-line slug if scope=='service_line', empty if universal. "
            "Examples: nri_tax, foreign_subsidiary, transfer_pricing, "
            "virtual_cfo, gst_indirect, secretarial_roc, audit."
        ),
    )
    scope: Scope
    confidence: float = Field(ge=0.0, le=1.0)


class LearnerClarification(BaseModel):
    question_text: str
    options: list[str] = Field(
        default_factory=list,
        description="Multi-choice options. Empty list means freetext answer.",
    )
    target_unit_index: int = Field(
        ge=0,
        description="0-based index into `units` that this question concerns.",
    )


class LearnerOutput(BaseModel):
    units: list[LearnerUnit]
    clarifications: list[LearnerClarification]


# --- Prompt ----------------------------------------------------------------


LEARNER_INSTRUCTIONS = """You are Anika's Learner. CA Prakasha (Senior Partner at Balakrishna & Co.)
is training Anika — his AI email-drafting assistant — by uploading teaching
content: past replies he is happy with, rules Anika should follow, firm
policies, fee structures, factual references about the firm or people.

Your job is to read the teaching content and extract structured *units*:

Unit kinds (choose exactly one per unit):
  - rule     : a do / don't / always / never statement. Short, imperative.
  - example  : an actual email or reply, verbatim or near-verbatim. Used as a
               voice sample for future drafts.
  - fact     : a static truth (phone number, fee structure, office address,
               partner credential). Not opinion.
  - policy   : a firm stance / positioning / philosophy (e.g., "we never
               guarantee outcomes in writing").

For each unit:
  - service_line : set this ONLY if the unit is specific to one area. Use a
                   stable slug: nri_tax, foreign_subsidiary, transfer_pricing,
                   virtual_cfo, gst_indirect, secretarial_roc, audit. Empty
                   string otherwise.
  - scope        : 'universal' if applies to every draft; 'service_line' if
                   specific. Must match service_line presence.
  - confidence   : your own 0-1 confidence in the above classification.

CLARIFICATION POLICY — be RUTHLESSLY skeptical. Over-clarifying is SAFER than wrong storage.

HARD AMBIGUITY TRIGGERS — confidence MUST be < 0.8, MUST generate clarification:
  - Any fee, amount, number, or rupee value WITHOUT an explicit service line named in the same unit
  - Content shorter than 15 words total
  - Words like "fee", "cost", "price", "charge", "rate" without a specific service context
  - A figure like "15000" or "Rs. X" where the service is not stated in the same line
  - A past email snippet where the service being discussed is not obvious from the text itself
  - Any entry that could plausibly apply to multiple service lines

CONFIDENCE SCORING RULES (be ruthlessly honest, do NOT default to 0.9):
  - Full sentence naming service line AND clear intent → 0.9+
  - Clear intent but service line missing → 0.3-0.6 (ALWAYS clarify)
  - Fragment, amount only, or ambiguous verb → 0.1-0.3 (ALWAYS clarify)
  - Very short input (under 15 words) → max 0.4 regardless

UNIVERSAL SCOPE RULE — apply ONLY when the unit provably applies to ALL service lines. If you would label something universal but cannot prove it applies to NRI tax AND foreign subsidiary AND GST AND audit AND everything else, flag it as a clarification instead. When in doubt about scope, ASK.

For every unit with confidence < 0.8, generate ONE clarification question.
Ambiguity triggers to watch for:
  - service line unclear (could apply to 2+ lines)
  - could be a rule or just an example
  - could be universal or service-specific
  - a fee mentioned but which service it attaches to is unclear
  - looks like a near-duplicate of an obvious common rule (let user confirm)

For each clarification:
  - Prefer `options` (2-4 concrete choices) when the space is finite.
  - Use an empty `options` list (freetext) only for open-ended cases.
  - target_unit_index = the 0-based position of the unit in `units`.

Splitting guidance:
  - If the upload is a single past email, usually ONE unit of kind='example'.
  - Do NOT split one email into multiple rule/fact units unless the email
    contains explicit list-like teaching ("Rule 1:", "Rule 2:", etc).
  - If the upload contains a numbered list or section headings, split
    accordingly — one unit per numbered item / section.

Output strict JSON matching LearnerOutput.
"""


# --- Helpers ---------------------------------------------------------------


def adaptive_clarification_limit(num_units: int) -> int:
    """Return the max clarifications to surface up-front for a single upload.

    Formula: max(3, min(10, ceil(num_units * 0.3))).
      - 1-10 units → 3 clarifications (always at least 3)
      - 20 units   → 6
      - 33+ units  → 10 (capped)
    """
    return max(3, min(10, math.ceil(num_units * 0.3)))


_PII_PHONE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
_PII_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
_PII_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def detect_pii_in_unit(content: str) -> list[str]:
    """Return a short list of PII types found in `content`.

    Used to flag units with third-party PII so the reviewer sees a banner.
    We do NOT block — the user is often intentionally teaching Anika a
    client's phone number — but we surface it so Prakash sir can decide.
    """
    hits: list[str] = []
    if _PII_PHONE.search(content):
        hits.append("phone")
    if _PII_EMAIL.search(content):
        hits.append("email")
    if _PII_PAN.search(content):
        hits.append("pan")
    return hits


# --- Agent + runner --------------------------------------------------------


def _build_agent() -> Agent:
    return Agent(
        name="TeachingLearner",
        instructions=LEARNER_INSTRUCTIONS,
        model=get_settings().openai_model_learner,
        output_type=LearnerOutput,
    )


async def extract(content: str, *, source_hint: str = "") -> LearnerOutput:
    """Run the Learner on `content`.

    Args:
        content: the raw teaching material (plain text).
        source_hint: one-line context about origin, e.g. "uploaded PDF
            'voice_guide.pdf' (3 pages)". Shown to the model verbatim.

    Returns:
        LearnerOutput with units and clarifications.
    """
    payload: dict[str, Any] = {
        "source_hint": source_hint,
        "content": content[:20000],  # hard cap — very long uploads get truncated
    }
    agent = _build_agent()
    with reasoning_log.timed(
        agent_name="teaching_learner",
        input_obj={"source_hint": source_hint, "content_chars": len(content)},
        model=get_settings().openai_model_learner,
    ) as ctx:
        result = await Runner.run(
            agent,
            input=(
                "Extract teaching units from this content. "
                "Return JSON matching LearnerOutput.\n\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
            max_turns=4,
        )
        output: LearnerOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = f"extracted {len(output.units)} units, {len(output.clarifications)} clarifications"
    return output


def cap_clarifications(output: LearnerOutput) -> tuple[list[LearnerClarification], list[LearnerClarification]]:
    """Split clarifications into (surface_now, defer_later) per the adaptive limit."""
    limit = adaptive_clarification_limit(len(output.units) or 1)
    return output.clarifications[:limit], output.clarifications[limit:]
