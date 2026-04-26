from pathlib import Path

# We add a parallel module rather than modifying purpose_classifier.py heavily.
# This keeps the core classifier clean while adding the humility layer.
module = """\"\"\"Humility layer — articulates what Anika noticed and what she needs.

When the purpose classifier returns low confidence (< 0.5) or when content
doesn't match any meta-rule, this layer generates a transparent request:
- What features Anika noticed in the content
- What she's uncertain about (specific ambiguity)
- What single focused question would help her learn

The output is shown to Prakasha sir so he can teach her. His answer becomes
both a library entry with a custom_purpose_label AND a new meta_rule.

Philosophy: Anika is honest about uncertainty. Unknown is a first-class
state, not a fallback. Every 'I don't know' is a teaching opportunity.

Runs on gpt-4o-mini. Output is Pydantic structured.
\"\"\"

from __future__ import annotations

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.config import get_settings


class UnknownArticulation(BaseModel):
    noticed_features: list[str] = Field(
        description=\"2-4 specific features Anika observed in the content (structure, tone, markers, format)\"
    )
    best_guess_purpose: str = Field(
        description=\"Her best guess among the 8 purposes, even if low confidence\"
    )
    best_guess_confidence: float = Field(
        ge=0.0, le=1.0,
        description=\"Honest confidence in the best guess\"
    )
    alternative_purposes: list[str] = Field(
        description=\"1-3 other purposes that could apply — shows Anika's actual uncertainty\"
    )
    uncertainty_source: str = Field(
        description=\"The SPECIFIC thing that makes classification hard. Name the ambiguity precisely.\"
    )
    single_focused_question: str = Field(
        description=\"ONE question for Prakasha sir that would resolve the uncertainty. Fast to answer. Respectful of his time.\"
    )
    suggested_custom_label: str | None = Field(
        default=None,
        description=\"If content seems to warrant a new purpose category, suggest a lowercase_snake_case label\"
    )


INSTRUCTIONS = \"\"\"You are Anika's humility layer. When you're uncertain about an upload, you articulate what you noticed, what confuses you, and what you need — respecting Prakasha sir's time.

PHILOSOPHY:
Anthropic-style honesty. Don't guess when unsure. Show reasoning. Ask precise questions. Uncertainty is not weakness — hidden uncertainty is.

WHAT TO PRODUCE:

1. noticed_features: 2-4 SPECIFIC things you observed in the content.
   - BAD: \"It's a document\" (too vague)
   - GOOD: \"Tabular structure with column headers\", \"Signature line at bottom\", \"ICICI Bank letterhead reference\"

2. best_guess_purpose: Your honest best guess from the 8 purposes. Even at low confidence, commit to ONE guess.

3. best_guess_confidence: Calibrated. 0.3-0.5 for genuine uncertainty. Higher means you shouldn't be in this humility mode at all.

4. alternative_purposes: 1-3 other purposes that also fit. Shows the actual branching.
   - If only 1 alternative → you have bimodal uncertainty
   - If 3 alternatives → genuine confusion
   - This makes your thinking visible to Prakasha sir

5. uncertainty_source: NAME THE SPECIFIC AMBIGUITY.
   - BAD: \"It's unclear\" (useless)
   - GOOD: \"This looks like a firm_fact because it states a number, but the number (Rs 5,00,000) could be a client's transaction, not the firm's fee.\"
   - BAD: \"Not sure which category\"
   - GOOD: \"The rule 'do not carry forward losses' could be firm_policy if Prakasha sir authored it, or reference_material if it's from a tax regulator.\"

6. single_focused_question: ONE question. Fast to answer. Not multiple.
   - BAD: \"What is this, how should I use it, which service line?\"
   - GOOD: \"Who authored this — you, or an external party (bank, regulator, vendor)?\"
   - BAD: \"Can you explain more about this document?\"
   - GOOD: \"Is this a firm policy you wrote, or regulatory guidance from ICAI?\"

7. suggested_custom_label: Only if the content seems to warrant a NEW purpose category (something none of the 8 capture). Use lowercase_snake_case.

QUALITY TEST:
- If Prakasha sir reads your articulation, does he IMMEDIATELY know why you're confused? Yes = good.
- Could your question be answered in 5 seconds? Yes = good.
- Would a different answer change your classification? Yes = good.

EXAMPLE:
Content: 'Section 54 exemption: Capital gains reinvested in new residential property within 2 years are exempt from tax.'

Output:
  noticed_features: ['Legal citation (Section 54)', 'Specific conditional rule about tax exemption', 'No salutation or signature']
  best_guess_purpose: 'domain_knowledge'
  best_guess_confidence: 0.45
  alternative_purposes: ['reference_material', 'firm_policy', 'workflow_rule']
  uncertainty_source: 'This is a tax law rule. It could be domain_knowledge (you want me to know the law), workflow_rule (you want me to apply this in NRI tax drafts), or firm_policy (this is how you advise all clients). The classification depends on HOW you want me to use it.'
  single_focused_question: 'Sir, when a client asks about capital gains, should I proactively mention this Section 54 exemption in drafts, or only reference it if I specifically search for it?'
  suggested_custom_label: null

Return UnknownArticulation JSON exactly.\"\"\"


def _build_agent() -> Agent:
    return Agent(
        name=\"HumilityLayer\",
        instructions=INSTRUCTIONS,
        model=get_settings().openai_model_classifier,
        output_type=UnknownArticulation,
    )


async def articulate_uncertainty(
    *,
    content: str,
    classifier_reasoning: str | None = None,
    filename: str | None = None,
) -> UnknownArticulation:
    \"\"\"When the classifier has low confidence, this layer articulates why.

    Called by the upload flow when purpose_classifier returns confidence < 0.5.
    \"\"\"
    agent = _build_agent()

    hint = f\"\\nFilename: {filename}\" if filename else \"\"
    classifier_note = f\"\\n\\nMain classifier said: {classifier_reasoning}\" if classifier_reasoning else \"\"

    user_prompt = f\"\"\"Articulate your uncertainty about this upload.
{hint}
{classifier_note}

CONTENT:
---
{content[:3000]}
---

Generate UnknownArticulation. Be specific about what you noticed and precise about what you need from Prakasha sir.\"\"\"

    result = await Runner.run(agent, input=user_prompt, max_turns=3)
    return result.final_output
"""

Path("app/agents/humility_layer.py").write_text(module, encoding="utf-8")
print("Wrote app/agents/humility_layer.py")

# Smoke test
import sys
sys.path.insert(0, ".")
from app.agents import humility_layer
print()
print("Module imports OK")
print(f"UnknownArticulation fields: {list(humility_layer.UnknownArticulation.model_fields.keys())}")
