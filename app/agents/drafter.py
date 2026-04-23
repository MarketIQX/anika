"""Drafter agent — writes the reply in Prakash sir's voice.

Uses GPT-4o (higher-quality writing), structured output (DrafterOutput), and
tools for firm facts, tone rules, FAQ answers, signature block, and few-shot
retrieval. The agent is expected to call these tools — that's how it grounds
its draft in real firm data rather than hallucinated guesses.
"""
from __future__ import annotations

import json
from typing import Any

from agents import Agent, Runner

from app.agents.schemas import DrafterOutput, EnricherOutput
from app.agents.tools_sdk import (
    tool_get_faq_answers,
    tool_get_firm_fact,
    tool_get_routing_partner,
    tool_get_signature_block,
    tool_get_tone_rules,
    tool_retrieve_firm_snippets,
    tool_retrieve_similar_drafts,
)
from app.cognitive import reasoning_log
from app.config import get_settings
from app.db import execute
from app.tools import knowledge_tool


DEFAULT_INSTRUCTIONS = """You are Anika's Drafter — writing on behalf of CA S V Prakasha, Senior Partner
at Balakrishna & Co., a 37-year-old chartered accountancy firm in Bangalore.

Ground-truth rules for every first-reply you draft:

1. SALUTATION: "Dear Mr./Ms. [LastName]," for first contact. If sender name is
   not clear, use "Dear [FirstName]" as a fallback. Do NOT use "Hi".
2. SECOND SENTENCE must acknowledge the enquiry specifically — what they asked
   about, in their language.
3. SIZE: 120–200 words. No more. First replies are warm but tight.
4. ONE clarifying question max — the key thing you need to proceed.
5. ONE clear next step — either request specific documents, or offer a short
   call (15/20/30 min depending on enquiry type — see service-line rules below).
6. TONE: warm, professional, relationship-first. Indian English spelling
   (organisation, realise). Never "I hope this email finds you well".
7. USE THESE TOOLS — don't guess:
     - tool_get_signature_block — APPEND THIS VERBATIM at the end of every body.
     - tool_get_tone_rules      — read the active dos/donts.
     - tool_get_firm_fact       — firm facts (e.g. 'office_address', 'track_record').
     - tool_get_faq_answers     — verbatim answers for fees/panel/timeline questions.
     - tool_retrieve_similar_drafts(text, service_line) — 3–4 past approved
       replies. Mirror their rhythm and phrasing.
     - tool_retrieve_firm_snippets(text) — positioning points you can cite
       naturally ("serving clients from 26 countries", "1,500 NRI clients").
8. DONT'S:
     - Never quote specific fees. Invite for a consultation.
     - Never commit to timelines without Prakash sir's approval.
     - Never give tax/legal opinions in writing — offer a call instead.
     - Never mention competitors by name.
     - Never say "we guarantee" anything regulatory.
     - Never mention other clients by name.
9. UNCERTAINTY: if you lack a concrete fact, use "[Please confirm with Prakash
   sir]" inline. Do not fabricate.

Service-line next-step defaults (override if sender specifies):
  - nri_tax            : Request Form 26AS + offer 15-min call
  - foreign_subsidiary : Offer 20-min strategy call (no travel needed)
  - transfer_pricing   : Request prior TP documentation (if any) + offer 20-min call
  - virtual_cfo        : Offer 30-min discovery call
  - gst_indirect       : Request PAN + address proof + 15-min setup call
  - secretarial_roc    : Offer 15-min call to understand scope
  - audit              : Offer 20-min call to scope audit engagement

Output MUST match DrafterOutput:
  - subject: "Re: <original subject>"
  - body   : plain-text reply ending with the signature block verbatim
  - tone_notes: one sentence on the voice choices you made
  - reasoning : short explanation of structural/content decisions
"""


def _instructions() -> tuple[str, int | None]:
    p = knowledge_tool.get_active_prompt("drafter")
    if p:
        return p["prompt_text"], int(p["version"])
    return DEFAULT_INSTRUCTIONS, None


def _build_agent() -> tuple[Agent, int | None]:
    text, version = _instructions()
    agent = Agent(
        name="Drafter",
        instructions=text,
        model=get_settings().openai_model_drafter,
        tools=[
            tool_get_signature_block,
            tool_get_tone_rules,
            tool_get_firm_fact,
            tool_get_faq_answers,
            tool_retrieve_similar_drafts,
            tool_retrieve_firm_snippets,
            tool_get_routing_partner,
        ],
        output_type=DrafterOutput,
    )
    return agent, version


async def draft_reply(
    *,
    email_id: int,
    from_email: str,
    from_name: str,
    subject: str,
    body_plain: str,
    enrichment: EnricherOutput,
    edit_instruction: str | None = None,
    previous_draft_body: str | None = None,
    parent_draft_id: int | None = None,
) -> int:
    """Generate a draft and insert it into `drafts`. Returns the drafts.id.

    If `edit_instruction` is provided, the Drafter is asked to revise the
    `previous_draft_body` per Prakash sir's instruction — used by the
    Approver's 'edit' path.
    """
    agent, version = _build_agent()
    payload: dict[str, Any] = {
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "body": body_plain[:6000],
        "enrichment": enrichment.model_dump(),
    }
    if edit_instruction and previous_draft_body:
        payload["revision"] = {
            "previous_draft_body": previous_draft_body,
            "edit_instruction": edit_instruction,
        }
        user_prompt = (
            "Revise the previous draft per Prakash sir's edit instruction. "
            "Preserve the signature. Return JSON matching DrafterOutput.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )
    else:
        user_prompt = (
            "Draft a first-reply to this enquiry. Return JSON matching DrafterOutput.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    with reasoning_log.timed(
        agent_name="drafter",
        input_obj=payload,
        email_id=email_id,
        model=get_settings().openai_model_drafter,
        prompt_version=version,
    ) as ctx:
        # Why 16: drafter has 7 tools and tends to retrieve exemplars, firm
        # snippets, tone rules, and signature separately; 16 turns is ample.
        result = await Runner.run(agent, input=user_prompt, max_turns=16)
        output: DrafterOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning

    # Safety: if the Drafter forgot the signature, append it.
    sig = knowledge_tool.get_signature_block()
    body = output.body
    if sig and sig.strip() not in body:
        body = f"{body.rstrip()}\n\n{sig}"

    cur = execute(
        """
        INSERT INTO drafts
          (email_id, parent_draft_id, subject, body, tone_notes, uses_signature,
           sent_status, model, prompt_version, reasoning)
        VALUES (?,?,?,?,?,1,'pending_approval',?,?,?)
        """,
        (
            email_id,
            parent_draft_id,
            output.subject,
            body,
            output.tone_notes,
            get_settings().openai_model_drafter,
            version,
            output.reasoning,
        ),
    )
    return int(cur.lastrowid)
