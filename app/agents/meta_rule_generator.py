"""Meta-rule generator — takes a user correction and proposes a generalizable rule.

When Prakash sir uploads content and CORRECTS Anika's purpose classification,
this agent reads the specific example and generates a candidate rule that
generalizes the correction. The rule goes into meta_rules table and shapes
all future classifications.

Runs on gpt-4o-mini. Output is Pydantic structured.

The rule is presented to the user for approval/edit/discard before committing.
"""

from __future__ import annotations

from typing import Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.config import get_settings


VALID_PURPOSES = [
    "voice_example", "classifier_example", "document_type",
    "question_template", "workflow_rule", "firm_fact",
    "firm_policy", "reference_material",
]


class MetaRuleProposal(BaseModel):
    rule_text: str = Field(
        description="Natural language rule describing the pattern, max 200 chars. Written so Prakasha sir can read and verify intent."
    )
    trigger_pattern: str = Field(
        description="Plain-English description of what content triggers this rule (e.g. 'content starts with Never share or similar external security warnings')"
    )
    target_purpose: Literal[
        "voice_example", "classifier_example", "document_type",
        "question_template", "workflow_rule", "firm_fact",
        "firm_policy", "reference_material",
    ] = Field(description="The correct purpose to assign when trigger matches")
    target_service_line: str | None = Field(
        default=None,
        description="Optional service line (nri_tax, etc.)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How confident the meta-rule generalizes cleanly (0.9+ = very confident, 0.5-0.7 = specific case only)"
    )
    reasoning: str = Field(
        description="Short explanation of WHY this rule captures the correction's intent"
    )


INSTRUCTIONS = """You are Anika's meta-rule generator. CA Prakasha (Senior Partner, Balakrishna & Co.) is training Anika, his AI assistant. Anika classified an upload wrongly. Prakasha sir corrected it. Your job: look at the specific example and generalize it into a REUSABLE RULE that prevents the same mistake in future.

GOAL: Capture Prakasha sir's implicit reasoning so Anika's classifier agent can apply it forever.

KEY PRINCIPLES:

1. GENERALIZE, don't just restate the example. A rule that only matches the exact text is useless. Extract the PATTERN.

   BAD: "When content says 'Never share your OTP, CVV...', classify as reference_material"
   GOOD: "Rules and warnings written by external parties (banks, vendors) — not by the firm — are reference_material, not firm_policy"

2. CAPTURE THE 'WHY', not just the 'what'. The user corrected because of an underlying reason. Name that reason.

3. KEEP RULES ACTIONABLE. The rule text must be specific enough that the classifier agent can apply it confidently. Vague rules are worse than no rules.

4. BE HONEST ABOUT CONFIDENCE:
   - 0.9+ → The pattern generalizes cleanly across many future cases
   - 0.6-0.8 → The rule captures a useful pattern but may have edge cases
   - 0.3-0.5 → This is really just a specific case, not a general rule
   - Below 0.3 → Maybe don't create a rule at all

5. THE RULE FORMAT:
   - rule_text: natural language Prakasha sir can read and verify ('Banks' security warnings are reference_material')
   - trigger_pattern: plain English describing what content qualifies ('content is an external party security warning, e.g. bank OTP warnings')
   - target_purpose: the correct purpose
   - target_service_line: only if the correction specifically involves a service line

EXAMPLES:

Example 1:
Content: 'Never share your OTP, CVV or passwords with anyone, even if the person claims to be a Bank employee.'
Anika proposed: firm_policy
User confirmed: reference_material
Generated rule:
  rule_text: 'Security warnings written by banks or external vendors (not by Balakrishna & Co.) are reference_material, not firm_policy. Firm_policy applies only to rules authored by Prakasha sir or the firm.'
  trigger_pattern: 'Content is a security warning, policy, or rule authored by a bank, vendor, regulator, or other external party — not by the firm itself.'
  target_purpose: reference_material
  confidence: 0.9
  reasoning: 'The correction reveals a distinction between firm-authored policies (auto-apply to drafts) and externally-authored policies (store but never quote).'

Example 2:
Content: 'Transaction Types Include: RCHG - Recharge, DTAX - Direct Tax, BPAY - Bill payment...'
Anika proposed: reference_material
User confirmed: document_type
Generated rule:
  rule_text: 'Lists of structured codes, field definitions, or legend entries from a document are document_type, teaching Anika how to read similar documents.'
  trigger_pattern: 'Content is a structured list of codes, abbreviations, field definitions, or transaction types used in a specific document category.'
  target_purpose: document_type
  confidence: 0.85
  reasoning: 'Even isolated code lists teach Anika document anatomy — she needs to recognize these fields when reading actual client documents.'

Return MetaRuleProposal JSON exactly."""


def _build_agent() -> Agent:
    return Agent(
        name="MetaRuleGenerator",
        instructions=INSTRUCTIONS,
        model=get_settings().openai_model_classifier,
        output_type=MetaRuleProposal,
    )


async def generate_meta_rule(
    *,
    content: str,
    anika_proposed: str,
    user_confirmed: str,
    custom_label: str | None = None,
    service_line: str | None = None,
) -> MetaRuleProposal:
    """Generate a candidate meta-rule from a user correction."""
    agent = _build_agent()

    custom_note = f"\nUser also provided custom label: '{custom_label}'" if custom_label else ""
    sl_note = f"\nService line context: {service_line}" if service_line else ""

    user_prompt = f"""Prakasha sir corrected Anika's classification. Generate a generalizable meta-rule.

CONTENT Prakasha sir uploaded:
---
{content[:3000]}
---

Anika proposed: {anika_proposed}
Prakasha sir confirmed: {user_confirmed}{custom_note}{sl_note}

Generate a MetaRuleProposal that captures WHY Prakasha sir made this correction in a way that generalizes to future uploads."""

    result = await Runner.run(agent, input=user_prompt, max_turns=3)
    return result.final_output
