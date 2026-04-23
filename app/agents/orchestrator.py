"""Anika — the orchestrator.

Given one new email, Anika decides how to handle it. This module is the
control surface that ties classifier → enricher → (maybe) drafter → notify,
enforcing guardrails as hard code gates (not LLM-adjudicated).

Design decision — code orchestration over LLM orchestration:
  We run classifier, enricher, drafter as real Agents (each uses function
  calling with tools, each emits structured output, each is logged with
  chain-of-thought). The control flow between them is plain Python so the
  guardrails (kill switch, blacklist, VIP, daily cap) cannot be social-
  engineered away by a clever email. This is "fully agentic" at the
  decision level without abandoning safety.

Website-form substitution:
  The firm's website form sends enquiries TO prakasha@balakrishnaandco.com
  FROM the same address (via the mailer). Without intervention Anika would
  "reply" to Prakash sir himself. Before the classifier runs, we detect
  these via the web_form_parser and swap in the real enquirer's email,
  name, and message body. The original Gmail ids are preserved so we can
  still label the notification as processed.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from app.agents import classifier, drafter, enricher
from app.agents.schemas import Category, EnricherOutput
from app.cognitive import reasoning_log
from app.config import get_settings
from app.db import execute, fetch_one
from app.guardrails import kill_switch, topic_blacklist, vip_filter
from app.tools import gmail_tool, notify_tool, web_form_parser
from app.tools.gmail_tool import InboxMessage

logger = logging.getLogger(__name__)


def _maybe_substitute_web_form(msg: InboxMessage) -> tuple[InboxMessage, bool]:
    """If this is a website-form notification, return (substituted_msg, True).

    Substitution keeps the Gmail identifiers (message_id, thread_id) so we can
    still label it as processed, but swaps sender/body to the real enquirer.
    The outbound reply is later routed to the substituted from_email.
    """
    parsed = web_form_parser.parse(msg.body_plain, msg.body_html)
    if parsed is None:
        return msg, False

    # "Your enquiry to Balakrishna & Co" is a more sensible working subject
    # than the mailer's generic "Balakrishna and Co" — the Drafter will
    # usually echo this as "Re: Your enquiry to Balakrishna & Co".
    substituted_subject = "Your enquiry to Balakrishna & Co"

    new_msg = replace(
        msg,
        from_email=parsed.sender_email,
        from_name=parsed.sender_name,
        subject=substituted_subject,
        body_plain=parsed.message or msg.body_plain,
        body_html="",
        snippet=(parsed.message or "")[:200],
        is_reply_in_thread=False,  # a form submission is always first-contact
    )
    logger.info(
        "Web form detected — substituting sender %s -> %s",
        msg.from_email, parsed.sender_email,
    )
    return new_msg, True


def ingest_message(msg: InboxMessage, *, is_web_form: bool = False) -> int:
    """Insert a raw_emails row (idempotent on gmail_message_id). Return the id."""
    existing = fetch_one(
        "SELECT id FROM raw_emails WHERE gmail_message_id=?", (msg.message_id,)
    )
    if existing:
        return int(existing["id"])
    cur = execute(
        """
        INSERT INTO raw_emails
          (gmail_message_id, gmail_thread_id, from_email, from_name, to_email,
           cc, subject, body_plain, body_html, snippet, received_at,
           is_reply_in_thread, is_web_form)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            msg.message_id,
            msg.thread_id,
            msg.from_email,
            msg.from_name,
            msg.to_email,
            msg.cc,
            msg.subject,
            msg.body_plain,
            msg.body_html,
            msg.snippet,
            msg.received_at,
            1 if msg.is_reply_in_thread else 0,
            1 if is_web_form else 0,
        ),
    )
    return int(cur.lastrowid)


async def handle(msg: InboxMessage) -> dict[str, Any]:
    """Process one inbox message end to end.

    Returns a dict describing what happened (for logging / tests). Never
    raises on routine failures — agent errors are logged and we return
    a status.
    """
    # Web-form substitution happens BEFORE anything else touches `msg`:
    # the classifier, guardrails, and raw_emails row all see the real enquirer.
    msg, is_web_form = _maybe_substitute_web_form(msg)

    # Persist — even in kill-switch state, we still record it.
    email_id = ingest_message(msg, is_web_form=is_web_form)

    # Hard safety gate #1 — global kill switch.
    if kill_switch.is_on():
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={"email_id": email_id, "is_web_form": is_web_form},
            output_obj={"action": "skip", "reason": "kill_switch_on"},
            reasoning_text="kill switch is ON, no agents invoked",
            email_id=email_id,
        )
        return {"email_id": email_id, "action": "skip", "reason": "kill_switch_on"}

    # Hard safety gate #2 — sensitive content bypass.
    is_sensitive, reason = topic_blacklist.check(msg.subject, msg.body_plain)
    if is_sensitive:
        notify_tool.notify_sensitive_bypass(email_id, msg.from_email, msg.subject, reason)
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={"email_id": email_id, "is_web_form": is_web_form},
            output_obj={"action": "bypass_sensitive", "reason": reason},
            reasoning_text=f"sensitive content detected: {reason}",
            email_id=email_id,
        )
        _try_mark_processed(msg.message_id)
        return {"email_id": email_id, "action": "bypass_sensitive", "reason": reason}

    # Classifier first — agentic decision.
    cls = await classifier.classify(
        email_id=email_id,
        from_email=msg.from_email,
        from_name=msg.from_name,
        subject=msg.subject,
        body_plain=msg.body_plain,
        is_reply_in_thread=msg.is_reply_in_thread,
    )
    category: Category = cls.category

    if category not in ("new_enquiry", "existing_client"):
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={"email_id": email_id, "is_web_form": is_web_form},
            output_obj={"action": "skip_non_enquiry", "category": category},
            reasoning_text=f"category={category}, Anika does not draft for non-enquiries",
            email_id=email_id,
        )
        _try_mark_processed(msg.message_id)
        return {"email_id": email_id, "action": "skip_non_enquiry", "category": category}

    # Enricher — sender intelligence + service line.
    enr: EnricherOutput = await enricher.enrich(
        email_id=email_id,
        from_email=msg.from_email,
        from_name=msg.from_name,
        subject=msg.subject,
        body_plain=msg.body_plain,
    )

    # Hard safety gate #3 — VIP filter (summary-only, no auto-draft).
    vip_skip, vip_reason = vip_filter.should_skip_draft(msg.from_email)
    if vip_skip:
        notify_tool.notify_sensitive_bypass(email_id, msg.from_email, msg.subject, vip_reason)
        reasoning_log.log(
            agent_name="orchestrator",
            input_obj={"email_id": email_id, "is_web_form": is_web_form},
            output_obj={"action": "bypass_vip", "reason": vip_reason},
            reasoning_text=vip_reason,
            email_id=email_id,
        )
        _try_mark_processed(msg.message_id)
        return {"email_id": email_id, "action": "bypass_vip", "reason": vip_reason}

    # Drafter — write the reply.
    # For web forms we've already set a clean subject ("Your enquiry to
    # Balakrishna & Co"); the Drafter echoes it as "Re: ...". For regular
    # emails we still enforce the Re: prefix below.
    draft_id = await drafter.draft_reply(
        email_id=email_id,
        from_email=msg.from_email,
        from_name=msg.from_name,
        subject=msg.subject,
        body_plain=msg.body_plain,
        enrichment=enr,
    )
    # Enforce the 'Re: ' prefix if the drafter forgot — but only for regular
    # replies. Web-form drafts may or may not want "Re:"; leave them alone.
    if not is_web_form:
        needs_prefix = not msg.subject.lower().startswith("re:")
        row = fetch_one("SELECT subject FROM drafts WHERE id=?", (draft_id,))
        if row and needs_prefix and not (row["subject"] or "").lower().startswith("re:"):
            execute(
                "UPDATE drafts SET subject=? WHERE id=?",
                (f"Re: {row['subject']}", draft_id),
            )

    # Fire the approval-ready notification (Prakash sir gets a 1-line email).
    notify_tool.notify_draft_ready(
        draft_id=draft_id,
        sender_summary=enr.summary,
        service_line=enr.likely_service_line,
        urgency=enr.urgency,
    )

    reasoning_log.log(
        agent_name="orchestrator",
        input_obj={"email_id": email_id, "is_web_form": is_web_form},
        output_obj={
            "action": "drafted",
            "draft_id": draft_id,
            "category": category,
            "service_line": enr.likely_service_line,
            "urgency": enr.urgency,
            "is_web_form": is_web_form,
        },
        reasoning_text="new_enquiry drafted and notification sent",
        email_id=email_id,
    )
    _try_mark_processed(msg.message_id)
    return {"email_id": email_id, "action": "drafted", "draft_id": draft_id,
            "is_web_form": is_web_form}


def _try_mark_processed(gmail_message_id: str) -> None:
    """Best-effort: apply the Anika/Processed label. Never fatal, never
    removes UNREAD. Read-state belongs to Prakash sir."""
    if get_settings().anika_test_mode:
        return
    try:
        gmail_tool.mark_as_processed(gmail_message_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("mark_as_processed failed for %s: %s", gmail_message_id, e)
