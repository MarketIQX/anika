"""Enricher agent — sender intelligence and service-line routing.

Uses gpt-4o-mini, structured output (EnricherOutput), and three tools:
lookup_client, retrieve_similar_drafts, retrieve_firm_snippets. The agent
can call tools to ground its decisions in real data.
"""
from __future__ import annotations

import json
from typing import Any

from agents import Agent, Runner

from app.agents.schemas import EnricherOutput
from app.agents.tools_sdk import (
    tool_get_routing_partner,
    tool_lookup_client,
    tool_retrieve_firm_snippets,
    tool_retrieve_similar_drafts,
)
from app.cognitive import reasoning_log
from app.config import get_settings
from app.db import execute
from app.tools import knowledge_tool


DEFAULT_INSTRUCTIONS = """You are Anika's Enricher. Extract structured intelligence from this enquiry.

Your job is to answer: who is this sender, what do they likely want, how urgent
is it, and which partner should own it?

Use the tools available to you:
  - tool_lookup_client(email): is this an existing client?
  - tool_retrieve_similar_drafts(text, service_line): past approved replies
    for similar enquiries (useful for inferring service_line).
  - tool_retrieve_firm_snippets(text): firm positioning snippets.
  - tool_get_routing_partner(service_line): official routing matrix partner.

Service lines (pick exactly one, closest fit):
  - nri_tax            : NRI income tax, Schedule FA, NRI property, TDS, FEMA
  - foreign_subsidiary : India WOS/subsidiary/branch/LO for a foreign company
  - transfer_pricing   : TP study, Form 3CEB, related-party transactions
  - virtual_cfo        : startup CFO, valuation, fundraising, equity
  - gst_indirect       : GST registration/returns/audits, LUT, notices
  - secretarial_roc    : MCA filings, ROC compliance, director KYC
  - audit              : statutory/internal/tax audit
  - other              : doesn't fit cleanly

Urgency (use firm's lead-scoring rules):
  - hot  : foreign company wanting India entry; NRI with property sale;
           TP need; Section 195/DTAA on large remittances; foreigner starting
           business; NRI with unreported foreign assets.
  - warm : TP study for indian company with intl. txns; startup needing
           incorporation + GST + payroll; existing co. needing Virtual CFO.
  - cold : simple individual ITR, GST registration only, basic bookkeeping.

Summary: exactly 2 lines, plain text, suitable for a dashboard card. First line
states who + what they want; second line states suggested next step (call,
document request, etc.).

TOOL-CALL BUDGET (STRICT):
  - Use AT MOST 4 tool calls total across all tools.
  - After 4 tool calls, STOP calling tools and return your best-judgment output.
  - Missing data defaults:
      unknown service_line -> "other"
      unknown routing_partner -> "CA S V Prakasha"
      unknown urgency -> "warm"
      unknown sender -> treat as new_contact
  - Do NOT loop retrying the same tool. If a tool returns nothing, move on.
  - Incomplete is better than stuck.

Be concise. Return JSON matching EnricherOutput."""


def _instructions() -> tuple[str, int | None]:
    p = knowledge_tool.get_active_prompt("enricher")
    if p:
        return p["prompt_text"], int(p["version"])
    return DEFAULT_INSTRUCTIONS, None


def _build_agent() -> tuple[Agent, int | None]:
    text, version = _instructions()
    agent = Agent(
        name="Enricher",
        instructions=text,
        model=get_settings().openai_model_enricher,
        tools=[
            tool_lookup_client,
            tool_retrieve_similar_drafts,
            tool_retrieve_firm_snippets,
            tool_get_routing_partner,
        ],
        output_type=EnricherOutput,
    )
    return agent, version


async def enrich(
    *,
    email_id: int,
    from_email: str,
    from_name: str,
    subject: str,
    body_plain: str,
) -> EnricherOutput:
    """Run enrichment and persist the row."""
    agent, version = _build_agent()
    payload: dict[str, Any] = {
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "body": body_plain[:6000],
    }
    user_input = (
        "Enrich this enquiry. Return JSON matching EnricherOutput.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    client_match_id = None
    from app.tools import client_tool

    existing = client_tool.lookup_client(from_email)
    if existing:
        client_match_id = int(existing["id"])

    with reasoning_log.timed(
        agent_name="enricher",
        input_obj=payload,
        email_id=email_id,
        model=get_settings().openai_model_enricher,
        prompt_version=version,
    ) as ctx:
        # Why 12: the enricher has 4 tools and the model typically calls 2-3 of
        # them before committing to an output; 12 gives comfortable headroom.
        result = await Runner.run(agent, input=user_input, max_turns=12)
        output: EnricherOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning

    # Retrieve the set of memories we'd feed the Drafter — persist their ids.
    from app.cognitive import memory_core

    sims = memory_core.retrieve_few_shot(
        enquiry_text=f"{subject}\n\n{body_plain[:1500]}",
        service_line=output.likely_service_line,
        top_k=4,
    )
    memory_ids = [s["id"] for s in sims]

    execute(
        """
        INSERT INTO enrichments
          (email_id, sender_name, sender_org, sender_country, likely_service_line,
           urgency, routing_partner, similar_memories, client_match_id, summary,
           reasoning, model, prompt_version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            email_id,
            output.sender_name,
            output.sender_org,
            output.sender_country,
            output.likely_service_line,
            output.urgency,
            output.routing_partner,
            json.dumps(memory_ids),
            client_match_id,
            output.summary,
            output.reasoning,
            get_settings().openai_model_enricher,
            version,
        ),
    )
    return output
