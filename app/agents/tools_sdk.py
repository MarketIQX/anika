"""OpenAI Agents SDK tool adapters.

The Agents SDK's @function_tool decorator inspects docstrings and type hints
to expose Python functions to the model as tool calls. These adapters wrap
our pure tools (memory_tool, knowledge_tool, client_tool) so agents can
call them from within a Runner.run().

Design: each adapter has a one-sentence docstring — that's what the model
sees in the tool catalog. Keep them concise and truthful.
"""
from __future__ import annotations

from typing import Any

from agents import function_tool

from app.cognitive import memory_core
from app.tools import client_tool, knowledge_tool


# -------- Knowledge --------

@function_tool
def tool_get_firm_fact(key: str) -> str:
    """Return a firm-level fact by key. Unknown key → empty string.

    Typical keys: 'firm_name','office_address','positioning_statement',
    'track_record','signature_block'.
    """
    v = knowledge_tool.get_firm_fact(key)
    return v or ""


@function_tool
def tool_get_signature_block() -> str:
    """Return Prakash sir's signature block. The Drafter MUST append this to every reply."""
    return knowledge_tool.get_signature_block()


@function_tool
def tool_get_tone_rules() -> dict[str, list[str]]:
    """Return the firm's writing tone rules as {"dos": [...], "donts": [...]}."""
    return knowledge_tool.get_tone_rules()


@function_tool
def tool_get_faq_answers() -> list[dict[str, str]]:
    """Return verbatim FAQ answers [{"pattern": str, "answer": str}]. Reuse answers verbatim when applicable."""
    return knowledge_tool.get_faq_answers()


@function_tool
def tool_get_routing_partner(service_line: str) -> str:
    """Return the partner who owns this service line per the firm routing matrix.

    service_line is one of: nri_tax, foreign_subsidiary, transfer_pricing,
    virtual_cfo, gst_indirect, secretarial_roc, audit, other. Returns empty
    string if unknown.
    """
    routing = knowledge_tool.get_routing_matrix()
    for r in routing:
        if (r.get("key") or "").lower() == f"routing.{service_line.lower()}":
            return r.get("value") or ""
    return ""


# -------- Memory --------

@function_tool
def tool_retrieve_similar_drafts(enquiry_text: str, service_line: str | None = None) -> list[dict[str, Any]]:
    """Return up to 4 semantically similar past approved drafts + curated exemplars.

    Use these as few-shot examples for voice and structure. Each item has:
    {id, kind, service_line, subject, content, distance}.
    """
    return memory_core.retrieve_few_shot(enquiry_text, service_line=service_line, top_k=4)


@function_tool
def tool_retrieve_firm_snippets(enquiry_text: str) -> list[dict[str, Any]]:
    """Return firm positioning / track-record snippets relevant to the enquiry (up to 3)."""
    return memory_core.retrieve_firm_snippets(enquiry_text, top_k=3)


# -------- Clients --------

@function_tool
def tool_lookup_client(email: str) -> dict[str, Any]:
    """Look up an existing client by email. Returns the full row, or {} if none.

    Fields: id, email, name, organisation, country, is_vip, notes.
    """
    row = client_tool.lookup_client(email)
    return row or {}
