"""Purpose-classifier agent — analyzes uploaded content and proposes a purpose.

The agent takes raw teaching content (text or extracted from file) and returns:
  PurposeProposal {
    proposed_purpose:     one of the 8 valid purposes (see VALID_PURPOSES below)
    confidence:           0-1 self-assessed confidence
    reasoning:            natural language explanation
    suggested_service_line: optional service line (nri_tax, etc.) if applicable
    suggested_custom_label: if proposed_purpose looks like 'other', a suggested label
  }

This runs BEFORE the Learner's unit extraction. The user confirms/adjusts the
proposed purpose, then the Learner runs with purpose-specific extraction logic.

Runs on gpt-4o-mini. Output is Pydantic structured.
"""

from __future__ import annotations

from typing import Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import fetch_all


VALID_PURPOSES = [
    "voice_example",      # D1 — past reply Prakash sir wrote
    "classifier_example", # D2 — incoming email pattern
    "document_type",      # D3 — client document anatomy
    "question_template",  # D4 — clarifying questions per service
    "workflow_rule",      # D5 — next-step logic
    "firm_fact",          # D6a — firm data (fees, credentials)
    "firm_policy",        # D6b — rules to follow
    "reference_material", # Everything else — retrievable but not auto-used
]


class PurposeProposal(BaseModel):
    proposed_purpose: Literal[
        "voice_example", "classifier_example", "document_type",
        "question_template", "workflow_rule", "firm_fact",
        "firm_policy", "reference_material",
    ] = Field(description="One of 8 valid purposes")
    confidence: float = Field(ge=0.0, le=1.0, description="0-1 self-assessed confidence")
    reasoning: str = Field(description="Natural language explanation, 1-3 sentences")
    suggested_service_line: str | None = Field(
        default=None,
        description="Optional: nri_tax, foreign_subsidiary, transfer_pricing, virtual_cfo, gst_indirect, secretarial_roc, audit",
    )
    suggested_custom_label: str | None = Field(
        default=None,
        description="If content doesn't fit standard purposes cleanly, suggest a custom label",
    )


INSTRUCTIONS = """You are Anika's purpose classifier. CA Prakasha (Senior Partner at Balakrishna & Co.) is uploading content to train Anika, his AI email-drafting assistant.

Your job: read the content and classify what PURPOSE this upload serves. Each upload must be tagged with exactly ONE purpose so Anika's retrieval layer knows how to use it.

THE 8 PURPOSES:

1. voice_example — A past email reply Prakasha sir wrote. Usually starts with a salutation ('Dear Mr.', 'Dear Ms.'), addresses a client, ends with his signature block. Multiple paragraphs. Clearly a completed reply.

2. classifier_example — An example of an INCOMING email (from a client TO Prakasha sir). Teaches Anika to recognize a pattern of client enquiry. Often includes phrases like 'I am looking for...', 'I have a query...', 'Could you help with...'.

3. document_type — A sample of a document type Prakasha sir commonly receives (bank statement, Form 26AS, passport, engagement letter, tax notice). Teaches Anika the structure of such documents. Usually formal, tabular, with headers and fields.

4. question_template — A list of clarifying questions Prakasha sir asks clients for a specific service. 'For NRI tax, I always ask: residency status, filing years pending, capital gains...'. Short, enumerated questions.

5. workflow_rule — A rule about NEXT STEPS for a service line. 'For NRI tax first replies: request Form 26AS and offer a 15-min call.' 'For transfer pricing: escalate to Kumar Prasad.'

6. firm_fact — A factual statement about the firm. Fees ('Our NRI consultation fee is Rs 7,500'), credentials ('CA Prasad has 25 years experience'), addresses, team members, service offerings.

7. firm_policy — A behavioural rule Anika should ALWAYS follow in drafts. 'Never guarantee tax outcomes.' 'Always quote fees in writing when asked.' 'Never mention other clients by name.' Usually starts with 'always', 'never', or imperative verbs.

8. reference_material — Content that has value to store but should NOT be auto-quoted in drafts. Bank boilerplate (branch addresses, customer service numbers, OTP warnings), competitor marketing, old notifications. Anything that Prakasha sir might want to RETRIEVE later for audit/forensic/reference purposes, but which should NEVER appear in a client reply.

CLASSIFICATION RULES:

- If content has a salutation + body + signature → voice_example
- If content looks like an incoming email TO Prakasha sir → classifier_example
- If content has structured fields (Account Number, Period, Balance, etc.) → document_type
- If content is a list of questions → question_template
- If content describes what to DO (actions, next steps) → workflow_rule
- If content states a number, fee, credential, or firm identity → firm_fact
- If content is a rule/policy (always, never, must) → firm_policy
- If content is bank/vendor/system boilerplate that's just noise for drafting → reference_material

CONFIDENCE SCORING:
- Clear match to one category → 0.85-0.95
- Partial match or ambiguous → 0.5-0.7
- Could fit multiple categories → 0.3-0.5 (flag for clarification)
- No clear fit → suggest custom_label and use reference_material as default

SERVICE LINE:
- If content mentions a specific service (NRI tax, foreign subsidiary, GST, audit, transfer pricing, virtual CFO, secretarial/ROC), include it
- If content is firm-wide or unrelated to a single service, leave null

CUSTOM LABELS:
- If content doesn't fit any purpose well (e.g., 'this is an engagement letter template'), set suggested_custom_label
- Custom label should be lowercase_snake_case (engagement_letter, audit_finding, tp_documentation)

Return JSON matching PurposeProposal exactly. Be honest about uncertainty — low confidence is better than wrong assignment."""


def _build_agent() -> Agent:
    return Agent(
        name="PurposeClassifier",
        instructions=INSTRUCTIONS,
        model=get_settings().openai_model_classifier,  # gpt-4o-mini
        output_type=PurposeProposal,
    )


def _get_meta_rules_context() -> str:
    """Load active meta_rules and format them as context for the classifier."""
    rules = fetch_all(
        "SELECT rule_text, target_purpose, target_service_line FROM meta_rules WHERE is_active=1 ORDER BY priority DESC"
    )
    if not rules:
        return ""
    lines = ["\n\nMETA-RULES (user-defined overrides — apply these FIRST if trigger matches):"]
    for r in rules:
        lines.append(
            f"  - {r['rule_text']} → purpose={r['target_purpose']}" +
            (f", service_line={r['target_service_line']}" if r['target_service_line'] else "")
        )
    return "\n".join(lines)


async def classify_purpose(
    *,
    content: str,
    filename: str | None = None,
    file_mime: str | None = None,
) -> PurposeProposal:
    """Classify uploaded content. Returns PurposeProposal.

    Args:
        content: the raw teaching text (or extracted from file)
        filename: optional original filename for context
        file_mime: optional MIME type for context
    """
    agent = _build_agent()

    # Build the user prompt
    meta_context = _get_meta_rules_context()
    hint_lines = []
    if filename:
        hint_lines.append(f"Source filename: {filename}")
    if file_mime:
        hint_lines.append(f"MIME type: {file_mime}")
    source_hint = "\n".join(hint_lines)

    user_prompt = f"""Analyze this content and classify its purpose.
{source_hint}
{meta_context}

CONTENT:
---
{content[:4000]}
---

Return PurposeProposal JSON."""

    result = await Runner.run(agent, input=user_prompt, max_turns=3)
    return result.final_output
