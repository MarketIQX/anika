"""Dashboard routes — Inbox / Drafts / Train / Analytics / Settings.

Every route requires authentication. Role model:
  - admin : full access, including Train / Analytics / audit log / OAuth.
  - user  : Drafts + Inbox + limited Settings (kill switch, Gmail status,
            notifications view). Cannot manage clients, rules, or OAuth.

/healthz is the only intentionally-unauthenticated endpoint — used by the
Cloudflare Tunnel uptime probe.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.agents import approver
from app.auth import access_log
from app.auth.deps import client_ip, client_ua, current_user, require_admin, require_user
from app.auth.users import User
from app.config import get_settings
from app.db import execute, fetch_all, fetch_one
from app.guardrails import daily_cap, kill_switch
from app.jobs import backfill_memory, poll_gmail, weekly_review
from app.tools import client_tool, gmail_tool

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _fmt_json(v: Any) -> str:
    try:
        return json.dumps(json.loads(v) if isinstance(v, str) else v, indent=2, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return str(v)


templates.env.filters["pretty_json"] = _fmt_json


router = APIRouter()


def _common_context(request: Request, user: User) -> dict[str, Any]:
    return {
        "request": request,
        "gmail_connected": gmail_tool.has_credentials(),
        "kill_switch_on": kill_switch.is_on(),
        "cap_status": daily_cap.status(),
        "test_mode": get_settings().anika_test_mode,
        "current_user": user,
    }


# ---------------------------------------------------------------------------
# Health — intentionally unauthenticated. Used by uptime checks.
# ---------------------------------------------------------------------------


@router.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "gmail_connected": gmail_tool.has_credentials(),
        "kill_switch": "on" if kill_switch.is_on() else "off",
        "cap": daily_cap.status(),
    }


# ---------------------------------------------------------------------------
# Root → Drafts
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # If already authed, go to drafts; otherwise /drafts' own guard sends to /login.
    if current_user(request):
        return RedirectResponse("/drafts", status_code=302)
    return RedirectResponse("/login", status_code=302)


# ---------------------------------------------------------------------------
# Drafts — the approval queue
# ---------------------------------------------------------------------------


@router.get("/drafts", response_class=HTMLResponse)
async def drafts_index(request: Request, user: User = Depends(require_user)):
    pending = fetch_all(
        """
        SELECT d.id, d.subject, d.body, d.tone_notes, d.created_at, d.sent_status,
               e.summary, e.likely_service_line, e.urgency, e.routing_partner,
               r.from_email, r.from_name, r.subject AS orig_subject, r.body_plain AS orig_body
          FROM drafts d
          JOIN raw_emails r ON r.id = d.email_id
          LEFT JOIN enrichments e ON e.email_id = d.email_id
         WHERE d.sent_status = 'pending_approval'
         ORDER BY d.created_at DESC
        """
    )
    recent = fetch_all(
        """
        SELECT d.id, d.subject, d.sent_status, d.created_at,
               r.from_email, r.from_name
          FROM drafts d
          JOIN raw_emails r ON r.id = d.email_id
         WHERE d.sent_status IN ('sent','rejected','edited')
         ORDER BY d.created_at DESC
         LIMIT 20
        """
    )
    ctx = _common_context(request, user)
    ctx.update({"pending": pending, "recent": recent, "active_tab": "drafts"})
    return templates.TemplateResponse(request, "drafts.html", ctx)


@router.get("/drafts/{draft_id}", response_class=HTMLResponse)
async def draft_detail(request: Request, draft_id: int, user: User = Depends(require_user)):
    draft = fetch_one(
        """
        SELECT d.*, e.summary, e.likely_service_line, e.urgency, e.routing_partner,
               e.sender_name AS enr_name, e.sender_org, e.sender_country,
               r.from_email, r.from_name, r.subject AS orig_subject,
               r.body_plain AS orig_body, r.received_at
          FROM drafts d
          JOIN raw_emails r ON r.id = d.email_id
          LEFT JOIN enrichments e ON e.email_id = d.email_id
         WHERE d.id = ?
        """,
        (draft_id,),
    )
    if not draft:
        raise HTTPException(404, "draft not found")
    approvals_list = fetch_all(
        "SELECT * FROM approvals WHERE draft_id=? ORDER BY created_at DESC",
        (draft_id,),
    )
    reasoning = fetch_all(
        "SELECT agent_name, reasoning_text, output_json, latency_ms, created_at "
        "FROM reasoning_log WHERE email_id=? ORDER BY created_at ASC",
        (draft["email_id"],),
    )
    history = fetch_all(
        """
        SELECT id, subject, body, sent_status, created_at
          FROM drafts
         WHERE email_id=?
         ORDER BY created_at ASC
        """,
        (draft["email_id"],),
    )
    ctx = _common_context(request, user)
    ctx.update({
        "draft": draft,
        "approvals": approvals_list,
        "reasoning": reasoning,
        "history": history,
        "active_tab": "drafts",
    })
    return templates.TemplateResponse(request, "draft_detail.html", ctx)


@router.post("/drafts/{draft_id}/approve")
async def draft_approve(request: Request, draft_id: int, user: User = Depends(require_user)):
    try:
        result = await approver.approve(
            draft_id,
            decided_by=user.email,
            user_agent=client_ua(request),
            ip_address=client_ip(request),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("approve failed: %s", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    access_log.log(
        action="draft_approve",
        user_email=user.email,
        target=str(draft_id),
        ip_address=client_ip(request),
        user_agent=client_ua(request),
    )
    return RedirectResponse(
        f"/drafts/{draft_id}?sent=1&sent_log={result.get('sent_log_id','')}",
        status_code=303,
    )


@router.post("/drafts/{draft_id}/edit")
async def draft_edit(
    request: Request,
    draft_id: int,
    edit_instruction: str = Form(..., min_length=3),
    user: User = Depends(require_user),
):
    try:
        new_id = await approver.edit(
            draft_id,
            edit_instruction=edit_instruction,
            decided_by=user.email,
            user_agent=client_ua(request),
            ip_address=client_ip(request),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("edit failed: %s", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    access_log.log(
        action="draft_edit",
        user_email=user.email,
        target=str(draft_id),
        ip_address=client_ip(request),
        user_agent=client_ua(request),
    )
    return RedirectResponse(f"/drafts/{new_id}?edited_from={draft_id}", status_code=303)


@router.post("/drafts/{draft_id}/reject")
async def draft_reject(
    request: Request,
    draft_id: int,
    note: str | None = Form(None),
    user: User = Depends(require_user),
):
    try:
        approver.reject(
            draft_id,
            note=note,
            decided_by=user.email,
            user_agent=client_ua(request),
            ip_address=client_ip(request),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("reject failed: %s", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    access_log.log(
        action="draft_reject",
        user_email=user.email,
        target=str(draft_id),
        ip_address=client_ip(request),
        user_agent=client_ua(request),
    )
    return RedirectResponse(f"/drafts/{draft_id}?rejected=1", status_code=303)


# ---------------------------------------------------------------------------
# Inbox — classification history
# ---------------------------------------------------------------------------


@router.get("/inbox", response_class=HTMLResponse)
async def inbox_index(request: Request, user: User = Depends(require_user)):
    emails = fetch_all(
        """
        SELECT r.id, r.from_email, r.from_name, r.subject, r.received_at,
               c.category, c.confidence,
               d.id AS draft_id, d.sent_status
          FROM raw_emails r
          LEFT JOIN classifications c ON c.email_id = r.id
          LEFT JOIN drafts d ON d.email_id = r.id
         ORDER BY r.received_at DESC
         LIMIT 50
        """
    )
    ctx = _common_context(request, user)
    ctx.update({"emails": emails, "active_tab": "inbox"})
    return templates.TemplateResponse(request, "inbox.html", ctx)


@router.get("/inbox/{email_id}", response_class=HTMLResponse)
async def inbox_detail(request: Request, email_id: int, user: User = Depends(require_user)):
    email = fetch_one("SELECT * FROM raw_emails WHERE id=?", (email_id,))
    if not email:
        raise HTTPException(404, "email not found")
    classification = fetch_one(
        "SELECT * FROM classifications WHERE email_id=? ORDER BY id DESC LIMIT 1",
        (email_id,),
    )
    enrichment = fetch_one(
        "SELECT * FROM enrichments WHERE email_id=? ORDER BY id DESC LIMIT 1",
        (email_id,),
    )
    drafts = fetch_all(
        "SELECT * FROM drafts WHERE email_id=? ORDER BY created_at ASC", (email_id,)
    )
    reasoning = fetch_all(
        "SELECT * FROM reasoning_log WHERE email_id=? ORDER BY created_at ASC", (email_id,)
    )
    ctx = _common_context(request, user)
    ctx.update({
        "email": email,
        "classification": classification,
        "enrichment": enrichment,
        "drafts": drafts,
        "reasoning": reasoning,
        "active_tab": "inbox",
    })
    return templates.TemplateResponse(request, "inbox_detail.html", ctx)


# ---------------------------------------------------------------------------
# Train — admin only
# ---------------------------------------------------------------------------


@router.get("/train", response_class=HTMLResponse)
async def train_index(request: Request, user: User = Depends(require_admin)):
    prompts = fetch_all(
        """
        SELECT agent_name, version, change_note, is_active, created_at,
               substr(prompt_text, 1, 200) AS preview
          FROM agent_prompts
         ORDER BY agent_name, version DESC
        """
    )
    learner_events = fetch_all(
        """
        SELECT rl.created_at, rl.draft_id, rl.output_json, rl.reasoning_text
          FROM reasoning_log rl
         WHERE rl.agent_name = 'learner'
         ORDER BY rl.created_at DESC
         LIMIT 30
        """
    )
    approvals_stats = fetch_all(
        """
        SELECT decision, COUNT(*) n FROM approvals
         GROUP BY decision ORDER BY decision
        """
    )
    ctx = _common_context(request, user)
    ctx.update({
        "prompts": prompts,
        "learner_events": learner_events,
        "approvals_stats": approvals_stats,
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "train.html", ctx)


# ---------------------------------------------------------------------------
# Analytics — admin only
# ---------------------------------------------------------------------------


@router.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request, user: User = Depends(require_admin)):
    weekly = weekly_review.build_summary()
    latency = fetch_all(
        """
        SELECT agent_name, AVG(latency_ms) avg_ms, MAX(latency_ms) max_ms,
               COUNT(*) calls
          FROM reasoning_log
         WHERE created_at >= datetime('now','-7 days')
         GROUP BY agent_name
         ORDER BY agent_name
        """
    )
    recent_errors = fetch_all(
        """
        SELECT agent_name, error_text, created_at, email_id
          FROM reasoning_log
         WHERE status='error'
         ORDER BY created_at DESC LIMIT 20
        """
    )
    ctx = _common_context(request, user)
    ctx.update({
        "weekly": weekly,
        "latency": latency,
        "recent_errors": recent_errors,
        "active_tab": "analytics",
    })
    return templates.TemplateResponse(request, "analytics.html", ctx)


# ---------------------------------------------------------------------------
# Settings — both roles; UI hides admin-only controls via `is_admin`.
# ---------------------------------------------------------------------------


@router.get("/settings", response_class=HTMLResponse)
async def settings_index(request: Request, user: User = Depends(require_user)):
    # Admin-only pieces rendered conditionally in the template.
    vips = client_tool.list_vips() if user.is_admin else []
    clients = (
        fetch_all("SELECT id, email, name, organisation, is_vip FROM clients ORDER BY email")
        if user.is_admin else []
    )
    rules_rows = fetch_all("SELECT * FROM rules ORDER BY rule_type, id") if user.is_admin else []
    firm_facts = (
        fetch_all("SELECT key, value, category FROM firm_knowledge ORDER BY category, key")
        if user.is_admin else []
    )
    ctx = _common_context(request, user)
    ctx.update({
        "vips": vips,
        "clients": clients,
        "rules": rules_rows,
        "firm_facts": firm_facts,
        "active_tab": "settings",
        "notify_email": get_settings().notify_email,
        "public_base_url": get_settings().anika_public_base_url,
    })
    return templates.TemplateResponse(request, "settings.html", ctx)


@router.post("/settings/kill_switch")
async def toggle_kill_switch(
    request: Request,
    turn: str = Form(...),
    user: User = Depends(require_user),
):
    if turn == "on":
        kill_switch.set_on()
        access_log.log(action="kill_switch_on", user_email=user.email,
                       ip_address=client_ip(request), user_agent=client_ua(request))
    else:
        kill_switch.set_off()
        access_log.log(action="kill_switch_off", user_email=user.email,
                       ip_address=client_ip(request), user_agent=client_ua(request))
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/clients/add")
async def add_client(
    request: Request,
    email: str = Form(...),
    name: str = Form(""),
    organisation: str = Form(""),
    is_vip_flag: str = Form(""),
    user: User = Depends(require_admin),
):
    client_tool.upsert_client(
        email=email.strip(),
        name=name.strip() or None,
        organisation=organisation.strip() or None,
        is_vip_flag=(is_vip_flag.lower() == "on"),
    )
    access_log.log(action="client_add", user_email=user.email, target=email.strip().lower(),
                   ip_address=client_ip(request), user_agent=client_ua(request))
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/clients/{client_id}/vip")
async def toggle_vip(
    request: Request,
    client_id: int,
    vip: str = Form(...),
    user: User = Depends(require_admin),
):
    client_tool.set_vip(client_id, vip == "on")
    access_log.log(action="client_update_vip", user_email=user.email, target=str(client_id),
                   ip_address=client_ip(request), user_agent=client_ua(request))
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/clients/{client_id}/delete")
async def delete_client(
    request: Request,
    client_id: int,
    user: User = Depends(require_admin),
):
    client_tool.delete_client(client_id)
    access_log.log(action="client_delete", user_email=user.email, target=str(client_id),
                   ip_address=client_ip(request), user_agent=client_ua(request))
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/backfill_memory")
async def run_backfill_memory_with_vectors(
    request: Request,
    user: User = Depends(require_admin),
):
    try:
        counts = backfill_memory.run(seed_memory_vectors=True)
    except Exception as e:  # noqa: BLE001
        logger.exception("backfill_memory vectors failed: %s", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    access_log.log(action="memory_backfill", user_email=user.email,
                   ip_address=client_ip(request), user_agent=client_ua(request))
    return JSONResponse({"ok": True, "counts": counts})


@router.post("/settings/poll_now")
async def trigger_poll_now(
    request: Request,
    user: User = Depends(require_admin),
):
    n = await poll_gmail.poll_now()
    access_log.log(action="poll_now", user_email=user.email,
                   ip_address=client_ip(request), user_agent=client_ua(request))
    return JSONResponse({"ok": True, "processed": n})


@router.get("/settings/gmail/connect")
async def gmail_connect_start(
    request: Request,
    user: User = Depends(require_admin),
):
    access_log.log(action="gmail_oauth_start", user_email=user.email,
                   ip_address=client_ip(request), user_agent=client_ua(request))
    try:
        gmail_tool.authorize_interactive()
    except Exception as e:  # noqa: BLE001
        logger.exception("OAuth failed: %s", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    access_log.log(action="gmail_oauth_complete", user_email=user.email,
                   ip_address=client_ip(request), user_agent=client_ua(request))
    return RedirectResponse("/settings?gmail=connected", status_code=303)


# ---------------------------------------------------------------------------
# Audit log (admin only)
# ---------------------------------------------------------------------------


@router.get("/settings/audit", response_class=HTMLResponse)
async def settings_audit(request: Request, user: User = Depends(require_admin)):
    rows = access_log.recent(limit=300)
    ctx = _common_context(request, user)
    ctx.update({"rows": rows, "active_tab": "settings"})
    return templates.TemplateResponse(request, "audit.html", ctx)
