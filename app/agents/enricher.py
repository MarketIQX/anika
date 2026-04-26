"""Enricher agent — sender intelligence and service-line routing.

DESIGN (Phase 1B Cluster 4 — tool-less):
  - Old design: the agent had four tools (lookup_client, retrieve_similar_drafts,
    retrieve_firm_snippets, get_routing_partner) and was expected to decide
    when to call them. In practice this caused MaxTurnsExceeded loops on
    ambiguous emails (the model would re-call the same tool with different
    args trying to "make sense" of an enquiry).
  - New design: `enrich()` PRE-FETCHES the only two pieces of context the
    model actually needs (existing-client lookup + semantically similar past
    replies), inlines them into the user_input as structured PRE-FETCHED
    CONTEXT, and runs the agent tool-less. Model has nothing to call — it
    reads context and emits the structured EnricherOutput in a single turn.
  - max_turns drops from 20 to 3 because there are no tool round-trips.
  - The MaxTurnsExceeded heuristic fallback stays as defense-in-depth in
    case the model hits its own self-reflection ceiling.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from agents import Agent, Runner

from app.agents.schemas import EnricherOutput
from app.cognitive import memory_core, reasoning_log
from app.config import get_settings
from app.db import execute
from app.tools import client_tool, knowledge_tool

logger = logging.getLogger(__name__)


DEFAULT_INSTRUCTIONS = """You are Anika's Enricher. Extract structured intelligence from this enquiry.

Your job is to answer: who is this sender, what do they likely want, how urgent
is it, and which partner should own it?

You have NO tools. All the context you need is provided inline below as
PRE-FETCHED CONTEXT (existing-client match + semantically similar past
replies). Read it, decide, return.

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

Routing partner: pick the partner you'd assign based on service_line. If
unsure, default to "CA S V Prakasha".

Summary: exactly 2 lines, plain text, suitable for a dashboard card. First
line states who + what they want; second line states suggested next step
(call, document request, etc.).

DEFAULTS (use these immediately when uncertain):
  - unknown service_line  -> "other"
  - unknown routing_partner -> "CA S V Prakasha"
  - unknown urgency       -> "warm"
  - unknown sender_org    -> ""
  - unknown sender_country -> ""

Incomplete enrichment is FINE. You have ONE turn — read context, return
JSON matching EnricherOutput.
"""


def _instructions() -> tuple[str, int | None]:
    p = knowledge_tool.get_active_prompt("enricher")
    if p:
        return p["prompt_text"], int(p["version"])
    return DEFAULT_INSTRUCTIONS, None


def _build_agent() -> tuple[Agent, int | None]:
    """Tool-less Enricher.

    No tools=[...]. The agent reads the PRE-FETCHED CONTEXT in user_input and
    returns EnricherOutput in a single turn.
    """
    text, version = _instructions()
    agent = Agent(
        name="Enricher",
        instructions=text,
        model=get_settings().openai_model_enricher,
        output_type=EnricherOutput,
    )
    return agent, version


def _format_existing_client(c: dict[str, Any] | None) -> str:
    if not c:
        return "none"
    name = c.get("name") or ""
    org = c.get("organisation") or ""
    country = c.get("country") or ""
    is_vip = "yes" if c.get("is_vip") else "no"
    return f"id={c.get('id')} name={name!r} organisation={org!r} country={country!r} vip={is_vip}"


def _format_similar_drafts(rows: list[dict[str, Any]], max_excerpt_chars: int = 500) -> list[dict[str, str]]:
    out = []
    for r in rows:
        out.append({
            "id": r.get("id"),
            "service_line": r.get("service_line") or "",
            "subject": r.get("subject") or "",
            "excerpt": (r.get("content") or "")[:max_excerpt_chars],
        })
    return out


async def enrich(
    *,
    email_id: int,
    from_email: str,
    from_name: str,
    subject: str,
    body_plain: str,
) -> EnricherOutput:
    """Run enrichment with PRE-FETCHED CONTEXT and persist the row.

    Pre-fetch step: we look up the sender in `clients` and retrieve up to 4
    semantically similar past approved drafts BEFORE invoking the agent.
    Both go into the user_input as structured context. The agent receives
    no tools and emits its EnricherOutput in a single turn.
    """
    agent, version = _build_agent()

    # ---- pre-fetch ----
    existing = client_tool.lookup_client(from_email)
    client_match_id = int(existing["id"]) if existing else None

    similar = memory_core.retrieve_few_shot(
        enquiry_text=f"{subject}\n\n{body_plain[:1500]}",
        service_line=None,  # don't constrain — we don't know the service yet
        top_k=4,
    )

    # ---- compose the input ----
    payload: dict[str, Any] = {
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "body": body_plain[:6000],
    }
    pre_fetched = {
        "existing_client": _format_existing_client(existing),
        "similar_past_replies": _format_similar_drafts(similar),
    }
    user_input = (
        "Enrich this enquiry. Return JSON matching EnricherOutput.\n\n"
        "PRE-FETCHED CONTEXT (you have no tools — this is everything):\n"
        + json.dumps(pre_fetched, ensure_ascii=False, indent=2)
        + "\n\nENQUIRY:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    with reasoning_log.timed(
        agent_name="enricher",
        input_obj={
            "payload": payload,
            "pre_fetched_context": pre_fetched,
            "tool_less": True,
        },
        email_id=email_id,
        model=get_settings().openai_model_enricher,
        prompt_version=version,
    ) as ctx:
        # max_turns=3: tool-less single-turn run + tiny safety margin for
        # OpenAI's structured-output retry behaviour.
        try:
            result = await Runner.run(agent, input=user_input, max_turns=3)
            output: EnricherOutput = result.final_output  # type: ignore[assignment]
        except Exception as exc:
            from agents.exceptions import MaxTurnsExceeded
            if not isinstance(exc, MaxTurnsExceeded):
                raise
            # Defense-in-depth: even tool-less runs can in theory exhaust
            # turns if the model insists on revising. Fall back to a
            # heuristic enrichment so the pipeline keeps moving and the
            # partner sees an honest "I struggled" flag on the draft.
            logger.warning(
                "Enricher exhausted max_turns on email %s — falling back to heuristic defaults",
                email_id,
            )
            text_lower = ((subject or "") + " " + (body_plain or "")).lower()
            heuristic_sl = "other"
            for keyword, sl in [
                ("nri", "nri_tax"),
                ("foreign asset", "nri_tax"),
                ("schedule fa", "nri_tax"),
                ("nro account", "nri_tax"),
                ("nre account", "nri_tax"),
                ("subsidiary", "foreign_subsidiary"),
                ("incorporation", "foreign_subsidiary"),
                ("wos", "foreign_subsidiary"),
                ("transfer pric", "transfer_pricing"),
                ("3ceb", "transfer_pricing"),
                ("gst", "gst_indirect"),
                ("indirect tax", "gst_indirect"),
                ("audit", "audit"),
                ("roc", "secretarial_roc"),
                ("compliance", "secretarial_roc"),
                ("secretarial", "secretarial_roc"),
                ("cfo", "virtual_cfo"),
                ("startup", "virtual_cfo"),
            ]:
                if keyword in text_lower:
                    heuristic_sl = sl
                    break

            output = EnricherOutput(
                sender_name=from_name or "",
                sender_org="",
                sender_country="",
                likely_service_line=heuristic_sl,
                urgency="warm",
                routing_partner="CA S V Prakasha",
                summary=(
                    f"{from_name or from_email} sent an enquiry. "
                    f"Anika could not fully enrich this email — please read the original carefully."
                ),
                reasoning=(
                    "ENRICHMENT FALLBACK: Enricher exceeded max_turns budget on this email. "
                    "Service line inferred via keyword heuristic; sender details left blank. "
                    "Partner should review the original email closely before approving."
                ),
            )

        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning

    # Persist the same `similar` ids we pre-fetched (these are what the
    # Drafter will see again at draft time). Filtered to those whose
    # service_line matches the agent's chosen line, plus all universals.
    memory_ids = [
        s["id"] for s in similar
        if not s.get("service_line") or s.get("service_line") == output.likely_service_line
    ]

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
