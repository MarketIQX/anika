"""Classifier agent — 5-way categorization of incoming emails.

Uses gpt-4o-mini and structured output (ClassifierOutput).
"""
from __future__ import annotations

import json

from agents import Agent, Runner

from app.agents.schemas import ClassifierOutput
from app.cognitive import reasoning_log
from app.config import get_settings
from app.tools import knowledge_tool


DEFAULT_INSTRUCTIONS = """You are Anika's Classifier. Categorize the incoming email into exactly one bucket.

Buckets:
- new_enquiry     : a first-contact from someone asking about the firm's services.
                    Not a reply; the sender is not an existing client. This is the
                    ONLY bucket Anika acts on by drafting a reply.
- existing_client : an ongoing thread or a recognized client email asking about
                    their active engagement. Must be handled personally.
- sensitive       : legal notices, tax demands, complaints, disputes, scrutiny
                    under 148, regulatory audits, or any enquiry mentioning a
                    rupee value above 50 lakhs. Escalate to partner; no draft.
- automated       : calendar invites, delivery bounces, no-reply newsletters,
                    billing alerts from services.
- spam            : promotions, phishing, obvious marketing blasts.
- other           : anything that doesn't fit cleanly.

Rules:
- Be conservative: if in doubt between new_enquiry and sensitive, pick sensitive.
- Threaded replies (the email shows 'Re:' or mentions earlier correspondence)
  are existing_client unless clearly a fresh topic from a new sender.
- Use `confidence` in [0, 1]. <0.6 confidence must still commit to a bucket,
  but the reasoning should call out the ambiguity.
- Reasoning is one or two sentences, chain-of-thought style.

Output MUST conform exactly to the ClassifierOutput schema.
"""


def _instructions() -> tuple[str, int | None]:
    p = knowledge_tool.get_active_prompt("classifier")
    if p:
        return p["prompt_text"], int(p["version"])
    return DEFAULT_INSTRUCTIONS, None


def _build_agent() -> tuple[Agent, int | None]:
    text, version = _instructions()
    agent = Agent(
        name="Classifier",
        instructions=text,
        model=get_settings().openai_model_classifier,
        output_type=ClassifierOutput,
    )
    return agent, version


async def classify(
    *,
    email_id: int,
    from_email: str,
    from_name: str,
    subject: str,
    body_plain: str,
    is_reply_in_thread: bool,
) -> ClassifierOutput:
    """Classify a single email and persist the classification + reasoning log."""
    agent, version = _build_agent()
    payload = {
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "is_reply_in_thread": is_reply_in_thread,
        "body": body_plain[:6000],  # cap to keep tokens predictable
    }
    user_input = (
        "Classify this email. Return JSON matching ClassifierOutput.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    with reasoning_log.timed(
        agent_name="classifier",
        input_obj=payload,
        email_id=email_id,
        model=get_settings().openai_model_classifier,
        prompt_version=version,
    ) as ctx:
        result = await Runner.run(agent, input=user_input, max_turns=2)
        output: ClassifierOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning

    # Persist the classification.
    from app.db import execute

    execute(
        """
        INSERT INTO classifications
          (email_id, category, confidence, reasoning, model, prompt_version)
        VALUES (?,?,?,?,?,?)
        """,
        (
            email_id,
            output.category,
            output.confidence,
            output.reasoning,
            get_settings().openai_model_classifier,
            version,
        ),
    )
    return output
