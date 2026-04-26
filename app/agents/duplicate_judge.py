"""Duplicate-rule judge — decides if a proposed meta-rule duplicates an existing one.

Anthropic-style approach: no fixed similarity threshold. Embeddings rank
candidates (efficient retrieval). An LLM reads both rules and judges whether
they capture the SAME underlying principle — not just whether the words are
similar.

This respects Prakasha sir's nuanced corrections. Two rules with similar
wording may actually encode different principles (e.g., 'external warnings'
vs 'outdated content' — both might read as 'not firm_policy' but for
different reasons).

Flow:
  1. New meta-rule proposed by meta_rule_generator
  2. Embed its trigger_pattern + fetch top 5 most similar existing active rules
  3. Send all to the judge agent
  4. Judge returns: duplicate_of (rule id or null) + reasoning

If duplicate → user sees both rules and decides: create anyway / merge / skip
If not → create new rule

Runs on gpt-4o-mini. Output is Pydantic structured.
"""

from __future__ import annotations

from typing import Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import fetch_all


class DuplicateJudgment(BaseModel):
    is_duplicate: bool = Field(
        description="True if any existing rule captures the SAME underlying principle"
    )
    duplicate_of_id: int | None = Field(
        default=None,
        description="If is_duplicate=True, the id of the matching existing rule"
    )
    reasoning: str = Field(
        description="Natural language — why this is or is not a duplicate. Name the specific shared principle or the specific difference."
    )
    difference_if_similar: str | None = Field(
        default=None,
        description="If rules look similar but capture DIFFERENT principles, describe the difference precisely"
    )


INSTRUCTIONS = """You are Anika's duplicate-rule judge. CA Prakasha corrects Anika and her system proposes meta-rules that generalize corrections. Your job: when a new meta-rule is proposed, judge whether any existing rule ALREADY captures the same principle.

YOU ARE NOT DECIDING ON TEXT SIMILARITY. You are deciding on PRINCIPLE SIMILARITY.

KEY PRINCIPLE:
Two rules are duplicates if — and ONLY if — applying either would produce the same classification on the same future content. If they might diverge on any plausible content, they are NOT duplicates.

HOW TO JUDGE:

1. Read the new rule's text, trigger, and target.
2. For each existing candidate rule, ask:
   - Would this rule and the new rule fire on the exact same types of content?
   - Is the underlying REASON for classification the same?
   - If I removed one, would anything be lost?

3. NAME THE SHARED PRINCIPLE (if duplicate) or the DIFFERENCE (if not):
   - "Both classify external security warnings as reference_material → duplicate"
   - "One catches external party warnings; the other catches outdated advice. Different principles → NOT duplicate"

4. BE CONSERVATIVE about declaring duplicates:
   - When in doubt → NOT duplicate (preserves the signal)
   - When confident the principles are identical → duplicate
   - Prakasha sir's nuanced distinctions must be preserved

EXAMPLES:

Example 1 — True duplicate:
New: 'Security warnings from banks are reference_material, not firm_policy'
Existing #12: 'Warnings written by external parties (banks, vendors) are reference_material'
Judgment: is_duplicate=True, duplicate_of_id=12
Reasoning: 'Both rules capture the same principle: external-party warnings belong in reference_material, not firm_policy. They would fire on identical content.'

Example 2 — Similar text, different principle:
New: 'Outdated notifications from system emails are reference_material'
Existing #12: 'Warnings written by external parties are reference_material'
Judgment: is_duplicate=False
Reasoning: 'Both target reference_material but for different reasons. One filters by authorship (external party); the other filters by staleness (outdated). An email could be outdated-but-internal, or current-but-external — they would diverge.'
difference_if_similar: 'New rule is about temporal staleness; existing rule is about authorship.'

Example 3 — Close but distinct:
New: 'Questions lists for transfer pricing service → question_template with service_line=transfer_pricing'
Existing #5: 'Questions lists for NRI tax service → question_template with service_line=nri_tax'
Judgment: is_duplicate=False
Reasoning: 'Both are question_templates but scoped to different service lines. The service line distinction must be preserved — NRI tax and transfer pricing require different questions.'

Return DuplicateJudgment JSON exactly. When uncertain, err toward is_duplicate=False."""


def _build_agent() -> Agent:
    return Agent(
        name="DuplicateJudge",
        instructions=INSTRUCTIONS,
        model=get_settings().openai_model_classifier,
        output_type=DuplicateJudgment,
    )


async def judge_duplicate(
    *,
    new_rule_text: str,
    new_trigger: str,
    new_target_purpose: str,
    new_target_service_line: str | None = None,
) -> DuplicateJudgment:
    """Judge if this new meta-rule duplicates an existing active rule.

    Uses embedding retrieval for efficiency (top-5 candidates), then LLM
    judgment for the actual duplicate decision.
    """
    # Fetch top candidates from existing active rules.
    # For now, fetch ALL active rules (we have few) — embedding-based top-k
    # becomes important when rule count grows beyond 50.
    existing = fetch_all("""
        SELECT id, rule_text, trigger_pattern, target_purpose, target_service_line
          FROM meta_rules
         WHERE is_active = 1
         ORDER BY priority DESC, id DESC
         LIMIT 20
    """)

    if not existing:
        # No existing rules — by definition not a duplicate
        return DuplicateJudgment(
            is_duplicate=False,
            duplicate_of_id=None,
            reasoning="No existing meta-rules to compare against.",
        )

    # Format the candidates for the judge
    candidates_text = "\n\n".join(
        f"CANDIDATE #{r['id']}:\n  rule_text: {r['rule_text']}\n  trigger: {r['trigger_pattern']}\n  target_purpose: {r['target_purpose']}\n  target_service_line: {r['target_service_line'] or '-'}"
        for r in existing
    )

    agent = _build_agent()
    sl_note = f"\n  target_service_line: {new_target_service_line}" if new_target_service_line else ""
    user_prompt = f"""Judge whether this NEW rule duplicates any EXISTING rule.

NEW RULE:
  rule_text: {new_rule_text}
  trigger: {new_trigger}
  target_purpose: {new_target_purpose}{sl_note}

EXISTING RULES:
{candidates_text}

Apply the judgment principles. Be conservative — when in doubt, NOT duplicate."""

    result = await Runner.run(agent, input=user_prompt, max_turns=3)
    return result.final_output
