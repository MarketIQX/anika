"""Drafter — writes the reply, using a prompt assembled at runtime.

Old design (v1): a single static prompt stored in agent_prompts.

New design (v2 / Phase 1A):
  For every draft, we BUILD the prompt from:
    1. DRAFTER_HEADER          — hardcoded identity + voice-mirror instructions
    2. rules / policies        — retrieved from knowledge_library (universal +
                                 matched service_line)
    3. examples                — top-k semantically similar approved drafts
                                 retrieved from knowledge_library
    4. facts                   — retrieved from knowledge_library
    5. SIGNATURE_INSTRUCTION   — the locked signature block (firm_identity)
    6. OUTPUT_SCHEMA           — DrafterOutput schema hint

Every assembly is logged to reasoning_log so Admin Prompt Preview can show
exactly what the model saw.

The legacy `agent_prompts` rows for the drafter are retained for audit but
ignored by this module — see DEFAULT_INSTRUCTIONS at the bottom, which is
only used as a fallback if runtime assembly somehow produces nothing.
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
from app.cognitive import library, reasoning_log
from app.config import SIGNATURE_BLOCK, get_settings
from app.config.firm_identity import ensure_signature
from app.db import execute, fetch_one
from app.tools import knowledge_tool


# --------------------------------------------------------------------------
# Static / hardcoded pieces — these are code, not DB rows. They DO NOT
# appear in agent_prompts; changing them is a code change.
# --------------------------------------------------------------------------


DRAFTER_HEADER = """You are Anika's Drafter — writing on behalf of CA Prakasha,
Senior Partner at Balakrishna & Co.

YOUR JOB: Mirror CA Prakasha's demonstrated voice. You are NOT the author —
he is. Study the retrieved rules, examples, and facts below and produce a
new draft that he would recognise as his own words.

Mirror from the retrieved examples:
  - Salutation pattern
  - Opening sentence
  - Structure (paragraphs vs bullets vs framework)
  - Fee disclosure approach (almost always: do not quote specific fees)
  - Closing and sign-off pattern

HARD RULES:
  - Never fabricate facts, numbers, or events not in the current email or
    the retrieved facts below.
  - Never reference prior conversations that aren't explicitly mentioned.
  - Never mention competitors by name.
  - Never guarantee regulatory outcomes.
  - Use Indian English spelling (organisation, realise, favour).

If no service-line examples were retrieved, use neutral professional Indian
business English and note in `reasoning`: "No voice samples found for this
service line — recommend training Anika on this type.\""""


SIGNATURE_INSTRUCTION = f"""End every draft body with EXACTLY this signature block, verbatim, with no modifications and nothing after it:

{SIGNATURE_BLOCK}

Do not change the phone number, name, or any line. Do not add anything after this block."""


OUTPUT_SCHEMA_HINT = """Return JSON matching DrafterOutput exactly:
  subject     — "Re: <original subject>" unless the orchestrator set a
                fresh subject (web-form enquiries receive a clean subject).
  body        — plain-text body ending with the signature block above.
  tone_notes  — one sentence on the voice choices you made.
  reasoning   — 1–3 sentences on structural/content decisions, naming the
                example memory ids you mirrored (if any)."""


# Legacy fallback — only used if knowledge_library is totally empty. Even
# then the orchestrator should be training Anika before sends go out.
DEFAULT_INSTRUCTIONS = (
    DRAFTER_HEADER
    + "\n\n[No rules, examples, or facts yet in knowledge_library — "
    + "teach Anika first. See /train.]\n\n"
    + SIGNATURE_INSTRUCTION
    + "\n\n"
    + OUTPUT_SCHEMA_HINT
)


# --------------------------------------------------------------------------
# Runtime prompt assembly
# --------------------------------------------------------------------------


def _format_rules(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    lines = []
    for r in rows:
        tag = "universal" if r["scope"] == "universal" else f"[{r.get('service_line') or 'service'}]"
        lines.append(f"- {tag} ({r['kind']}) [id={r['id']}]: {r['content']}")
    return "RULES & POLICIES (retrieved):\n" + "\n".join(lines)


def _format_examples(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "EXAMPLES: (none retrieved — voice samples are missing for this service)"
    parts = ["EXAMPLES OF CA PRAKASHA'S VOICE (retrieved — mirror these):"]
    for r in rows:
        tag = f"[id={r['id']}"
        if r.get("service_line"):
            tag += f" · {r['service_line']}"
        tag += "]"
        parts.append(f"\n--- example {tag} ---\n{r['content']}")
    return "\n".join(parts)


def _format_facts(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    lines = ["FIRM FACTS (retrieved):"]
    for r in rows:
        scope = r.get("scope", "universal")
        tag = "universal" if scope == "universal" else f"[{r.get('service_line')}]"
        lines.append(f"- {tag} [id={r['id']}]: {r['content']}")
    return "\n".join(lines)


def assemble_prompt(
    *,
    service_line: str | None,
    enquiry_body: str,
) -> tuple[str, list[int]]:
    """Build the Drafter prompt at runtime. Returns (prompt_text, used_library_ids).

    used_library_ids lists every knowledge_library row that went into the
    prompt, so the orchestrator can bump applied_count after the draft lands.
    """
    rules = library.retrieve_rules(service_line)
    facts = library.retrieve_facts(service_line)
    # Semantic retrieval for examples — keyed by the actual enquiry body.
    examples = library.retrieve_examples(
        query_text=enquiry_body[:2000],
        service_line=service_line,
        top_k=5,
    )

    sections = [
        DRAFTER_HEADER,
        _format_rules(rules),
        _format_examples(examples),
        _format_facts(facts),
        SIGNATURE_INSTRUCTION,
        OUTPUT_SCHEMA_HINT,
    ]
    prompt = "\n\n".join(s for s in sections if s)

    ids = [r["id"] for r in rules] + [r["id"] for r in examples] + [r["id"] for r in facts]
    return prompt, ids


# --------------------------------------------------------------------------
# Agent build + runner
# --------------------------------------------------------------------------


def _build_agent(instructions: str) -> Agent:
    return Agent(
        name="Drafter",
        instructions=instructions,
        model=get_settings().openai_model_drafter,
        tools=[
            tool_get_signature_block,
            tool_get_tone_rules,
            tool_get_firm_fact,
            tool_get_faq_answers,
            tool_retrieve_similar_drafts,   # legacy memory table — kept as supplementary
            tool_retrieve_firm_snippets,
            tool_get_routing_partner,
        ],
        output_type=DrafterOutput,
    )


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

    For revisions (edit_instruction + previous_draft_body), the Drafter is
    asked to revise the previous draft per Prakasha sir's instruction.
    """
    service_line = enrichment.likely_service_line
    prompt, used_ids = assemble_prompt(service_line=service_line, enquiry_body=body_plain)

    agent = _build_agent(prompt)
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
            "Revise the previous draft per CA Prakasha's edit instruction. "
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
        input_obj={
            "payload": payload,
            "assembled_prompt": prompt,           # full prompt for admin preview
            "used_library_ids": used_ids,
            "runtime_assembly": True,
        },
        email_id=email_id,
        model=get_settings().openai_model_drafter,
    ) as ctx:
        result = await Runner.run(agent, input=user_prompt, max_turns=16)
        output: DrafterOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning

    # Backstop: force the signature block if the drafter omitted/edited it.
    body = ensure_signature(output.body)

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
            None,                 # prompt_version no longer meaningful — prompt is assembled
            output.reasoning,
        ),
    )
    draft_id = int(cur.lastrowid)

    # Credit every library entry that went into this draft.
    library.bump_applied(used_ids)
    return draft_id
