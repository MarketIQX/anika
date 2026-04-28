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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.agents import approver
from app.agents import purpose_classifier, humility_layer
from app.agents import meta_rule_generator, duplicate_judge
from app.auth import access_log
from app.auth.deps import client_ip, client_ua, current_user, require_admin, require_user
from app.auth.users import User
from app.cognitive import library as kb_library
from app.cognitive import teaching
from app.config import get_settings
from app.db import execute, fetch_all, fetch_one
from app.guardrails import daily_cap, drafting_paused, kill_switch
from app.jobs import backfill_memory, poll_gmail, weekly_review
from app.tools import client_tool, file_extractors, gmail_tool

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
               d.id AS draft_id, d.sent_status,
               r.is_web_form
          FROM raw_emails r
          LEFT JOIN classifications c ON c.email_id = r.id
          LEFT JOIN drafts d ON d.email_id = r.id
         WHERE (c.category = 'new_enquiry' OR r.is_web_form = 1)
           AND COALESCE(r.subject,'') NOT LIKE '%Payment%'
           AND COALESCE(r.subject,'') NOT LIKE '%outstanding%'
           AND COALESCE(r.subject,'') NOT LIKE '%Invoice%'
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
async def train_index(request: Request, user: User = Depends(require_user)):
    """Teaching dashboard — both roles can access.

    Sections:
      A. Pending clarifications (if any)
      B. Teach Anika (textarea + file drop)
      C. Knowledge library (rules / examples / facts / policies, filterable)
      D. Library export (admin + user)
      E. Admin prompt preview (admin only)
      +  Legacy agent_prompts table (admin only — kept for history/audit)
    """
    clarifications = teaching.pending_clarifications()
    # Phase 1B — pending purpose proposals awaiting Prakash sir's confirmation
    import json as _json
    _raw_proposals = fetch_all("""
        SELECT id, raw_content, source_type, original_filename, created_at,
               anika_proposed_purpose, anika_proposed_confidence,
               anika_reasoning, anika_suggested_sl, anika_suggested_custom,
               humility_articulation
          FROM teaching_queue
         WHERE awaiting_confirmation = 1
           AND anika_proposed_purpose IS NOT NULL
         ORDER BY created_at DESC
         LIMIT 10
    """)
    pending_proposals = []
    for p in _raw_proposals:
        p_dict = dict(p)
        # Parse the humility JSON if present
        h = p_dict.get("humility_articulation")
        if h:
            try:
                parsed = _json.loads(h)
                if "noticed_features" in parsed:
                    p_dict["humility"] = parsed
                else:
                    p_dict["humility"] = None
            except Exception:
                p_dict["humility"] = None
        else:
            p_dict["humility"] = None
        pending_proposals.append(p_dict)
    queue_recent = teaching.recent_queue(limit=10)

    # Library filter: ?kind=rule/example/fact/policy and ?service_line=...
    kind_filter = request.query_params.get("kind") or None
    sl_filter = request.query_params.get("service_line") or None
    entries = kb_library.list_entries(kind=kind_filter, service_line=sl_filter)

    # Counts per kind for the tab chips.
    kind_counts = {
        r["kind"]: int(r["n"])
        for r in fetch_all(
            "SELECT kind, COUNT(*) n FROM knowledge_library WHERE is_active=1 GROUP BY kind"
        )
    }

    prompts = []
    learner_events = []
    approvals_stats = []
    if user.is_admin:
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

    # Admin prompt preview — most recent drafter reasoning_log entry.
    prompt_preview = None
    if user.is_admin:
        row = fetch_one(
            """
            SELECT created_at, email_id, draft_id, input_json, reasoning_text
              FROM reasoning_log
             WHERE agent_name = 'drafter'
             ORDER BY id DESC LIMIT 1
            """
        )
        if row:
            try:
                import json as _json
                data = _json.loads(row["input_json"] or "{}")
                prompt_preview = {
                    "created_at": row["created_at"],
                    "draft_id": row["draft_id"],
                    "prompt_text": data.get("assembled_prompt") or "(legacy draft — runtime assembly not used)",
                    "used_library_ids": data.get("used_library_ids") or [],
                }
            except Exception:  # noqa: BLE001
                pass

    # Phase 1C-1 — self-measurement summary on the Train tab.
    from app.cognitive.draft_metrics import per_service_line_summary
    learning_curves = per_service_line_summary()

    # Phase 1C-2 — substring patterns Anika has noticed.
    from app.cognitive.pattern_miner import counts_by_status, list_open_patterns
    open_patterns = list_open_patterns(limit=50)
    pattern_counts = counts_by_status()

    ctx = _common_context(request, user)
    ctx.update({
        "pending_proposals": pending_proposals,
        "clarifications": clarifications,
        "queue_recent": queue_recent,
        "entries": entries,
        "kind_filter": kind_filter,
        "sl_filter": sl_filter,
        "kind_counts": kind_counts,
        "prompts": prompts,
        "learner_events": learner_events,
        "approvals_stats": approvals_stats,
        "prompt_preview": prompt_preview,
        "drafting_paused": drafting_paused.is_on(),
        "learning_curves": learning_curves,
        "open_patterns": open_patterns,
        "pattern_counts": pattern_counts,
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "train.html", ctx)


# --- Phase 1C-1: learning curves detail page -------------------------------


@router.get("/train/learning-curves", response_class=HTMLResponse)
async def train_learning_curves(request: Request, user: User = Depends(require_user)):
    """Detailed timeline view of every metric. Both roles can read this —
    Prakasha sir benefits from seeing the curve as much as AK does."""
    from app.cognitive.draft_metrics import per_service_line_summary, recent_metrics

    summary = per_service_line_summary()
    timeline = recent_metrics(limit=50)
    ctx = _common_context(request, user)
    ctx.update({
        "summary": summary,
        "timeline": timeline,
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "learning_curves.html", ctx)


# --- Teach (text + files) --------------------------------------------------


@router.post("/train/teach")
async def train_teach(
    request: Request,
    content: str = Form(""),
    files: list[UploadFile] = File(default_factory=list),
    user: User = Depends(require_user),
):
    """Accept a text paste and/or one-or-more files.

    NEW FLOW (Phase 1B):
      1. Create queue row with status='awaiting_confirmation'
      2. Run purpose_classifier to propose purpose
      3. If confidence < 0.5, also run humility_layer
      4. Store proposals on the queue row
      5. Do NOT finalize_queue yet — user must confirm via /train/teach/confirm
    """
    import json as _json
    import time

    uploads_dir = teaching._ensure_uploads_dir()
    created_ids: list[int] = []
    errors: list[str] = []

    async def _classify_and_persist(qid: int, raw_text: str, filename: str | None, mime: str | None):
        """Run classifier + optional humility, write back to queue row."""
        try:
            proposal = await purpose_classifier.classify_purpose(
                content=raw_text,
                filename=filename,
                file_mime=mime,
            )
        except Exception as e:
            errors.append(f"queue {qid} classify: {str(e)[:80]}")
            return

        humility_json = None
        if proposal.confidence < 0.5:
            try:
                articulation = await humility_layer.articulate_uncertainty(
                    content=raw_text,
                    classifier_reasoning=proposal.reasoning,
                    filename=filename,
                )
                humility_json = _json.dumps(articulation.model_dump())
            except Exception as e:
                errors.append(f"queue {qid} humility: {str(e)[:80]}")

        execute(
            """
            UPDATE teaching_queue SET
                anika_proposed_purpose = ?,
                anika_proposed_confidence = ?,
                anika_reasoning = ?,
                anika_suggested_sl = ?,
                anika_suggested_custom = ?,
                humility_articulation = ?,
                status = ?,
                awaiting_confirmation = 1
             WHERE id = ?
            """,
            (
                proposal.proposed_purpose,
                proposal.confidence,
                proposal.reasoning,
                proposal.suggested_service_line,
                proposal.suggested_custom_label,
                humility_json,
                "processing",
                qid,
            ),
        )

    content = (content or "").strip()
    if content:
        qid = teaching.enqueue_text(raw_content=content, created_by=user.email)
        await _classify_and_persist(qid, content, None, None)
        created_ids.append(qid)

    for uf in files:
        if not uf.filename:
            continue
        body = await uf.read()
        if len(body) > file_extractors.MAX_UPLOAD_BYTES:
            errors.append(f"{uf.filename}: exceeds 50 MB limit")
            continue
        stem = Path(uf.filename).stem
        suffix = Path(uf.filename).suffix.lower()
        stamp = int(time.time() * 1000)
        safe_name = f"{stamp}__{stem}{suffix}"
        target = uploads_dir / safe_name
        target.write_bytes(body)
        try:
            extracted = file_extractors.extract(target)
        except file_extractors.FileTooLargeError as e:
            errors.append(f"{uf.filename}: {e}")
            continue
        except file_extractors.ExtractionError as e:
            errors.append(f"{uf.filename}: {e}")
            continue
        qid = teaching.enqueue_file(
            raw_content=extracted.text,
            file_mime=uf.content_type,
            original_filename=uf.filename,
            stored_path=str(target.relative_to(uploads_dir.parent.parent)),
            created_by=user.email,
        )
        await _classify_and_persist(qid, extracted.text, uf.filename, uf.content_type)
        created_ids.append(qid)

    access_log.log(
        action="teach_submit",
        user_email=user.email,
        target=",".join(str(i) for i in created_ids),
        ip_address=client_ip(request), user_agent=client_ua(request),
    )

    flash = "; ".join(errors)[:300] if errors else ""
    qs = f"?flash={flash}" if flash else ""
    return RedirectResponse(f"/train{qs}", status_code=303)


# --- Teach confirmation (Phase 1B feedback loop) --------------------------


@router.post("/train/teach/confirm")
async def train_teach_confirm(
    request: Request,
    queue_id: int = Form(...),
    confirmed_purpose: str = Form(...),
    custom_label: str = Form(""),
    service_line: str = Form(""),
    user: User = Depends(require_user),
):
    """Prakash sir confirms or corrects Anika's proposed purpose.

    If confirmed matches proposed → finalize queue as-is.
    If corrected → generate meta-rule proposal (not saved yet),
    store it on the queue, redirect to rule-review screen.
    """
    import json as _json

    queue_row = fetch_one("SELECT * FROM teaching_queue WHERE id = ?", (queue_id,))
    if not queue_row:
        return JSONResponse({"ok": False, "error": "queue not found"}, status_code=404)

    proposed = queue_row["anika_proposed_purpose"]
    is_correction = (confirmed_purpose != proposed)

    # Persist user confirmation immediately
    execute(
        """UPDATE teaching_queue SET
              awaiting_confirmation = 0,
              status = ?
           WHERE id = ?""",
        ("approved", queue_id),
    )

    access_log.log(
        action="teach_confirm",
        user_email=user.email,
        target=f"{queue_id}:{proposed}->{confirmed_purpose}",
        ip_address=client_ip(request), user_agent=client_ua(request),
    )

    # If it was a correction, generate meta-rule
    meta_rule_payload = None
    if is_correction:
        try:
            rule = await meta_rule_generator.generate_meta_rule(
                content=queue_row["raw_content"],
                anika_proposed=proposed or "unknown",
                user_confirmed=confirmed_purpose,
                custom_label=(custom_label or None),
                service_line=(service_line or None),
            )
            # Check for duplicate
            dup = await duplicate_judge.judge_duplicate(
                new_rule_text=rule.rule_text,
                new_trigger=rule.trigger_pattern,
                new_target_purpose=rule.target_purpose,
                new_target_service_line=rule.target_service_line,
            )
            meta_rule_payload = {
                "rule": rule.model_dump(),
                "duplicate_check": dup.model_dump(),
            }
        except Exception as e:  # noqa: BLE001
            meta_rule_payload = {"error": str(e)[:200]}

    # Store the meta-rule proposal on the queue row for the review screen
    if meta_rule_payload:
        execute(
            "UPDATE teaching_queue SET humility_articulation = ? WHERE id = ?",
            (_json.dumps({"pending_rule_review": meta_rule_payload}), queue_id),
        )
        # Redirect to the rule review screen for this queue
        return RedirectResponse(f"/train/review-rule/{queue_id}", status_code=303)

    # No correction → finalize with user-confirmed purpose (creates library entry)
    try:
        await teaching.finalize_with_purpose(
            queue_id,
            confirmed_purpose=confirmed_purpose,
            custom_label=(custom_label or None),
            service_line=(service_line or None),
            created_by=user.email,
        )
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": f"finalize failed: {e}"},
            status_code=500,
        )

    return RedirectResponse("/train", status_code=303)


@router.get("/train/review-rule/{queue_id}", response_class=HTMLResponse)
async def train_review_rule(
    request: Request,
    queue_id: int,
    user: User = Depends(require_user),
):
    """Show Prakash sir the meta-rule Anika proposed after his correction.
    He approves / edits / skips."""
    import json as _json

    queue_row = fetch_one("SELECT * FROM teaching_queue WHERE id = ?", (queue_id,))
    if not queue_row:
        raise HTTPException(status_code=404, detail="queue not found")

    rule_data = None
    if queue_row["humility_articulation"]:
        try:
            payload = _json.loads(queue_row["humility_articulation"])
            rule_data = payload.get("pending_rule_review")
        except Exception:  # noqa: BLE001
            pass

    ctx = _common_context(request, user)
    ctx.update({
        "queue_row": dict(queue_row),
        "rule_data": rule_data,
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "review_rule.html", ctx)


@router.post("/train/review-rule/{queue_id}/decide")
async def train_review_rule_decide(
    request: Request,
    queue_id: int,
    decision: str = Form(...),   # "accept", "edit", "skip"
    rule_text: str = Form(""),
    trigger_pattern: str = Form(""),
    target_purpose: str = Form(""),
    target_service_line: str = Form(""),
    priority: int = Form(0),
    user: User = Depends(require_user),
):
    """Accept, edit, or skip the proposed meta-rule, then finalize the queue."""
    import json as _json

    queue_row = fetch_one("SELECT * FROM teaching_queue WHERE id = ?", (queue_id,))
    if not queue_row:
        return JSONResponse({"ok": False, "error": "queue not found"}, status_code=404)

    if decision in ("accept", "edit"):
        # Parse the existing proposal
        payload = _json.loads(queue_row["humility_articulation"] or "{}")
        proposed_rule = payload.get("pending_rule_review", {}).get("rule", {})

        final_rule_text = rule_text or proposed_rule.get("rule_text", "")
        final_trigger = trigger_pattern or proposed_rule.get("trigger_pattern", "")
        final_target = target_purpose or proposed_rule.get("target_purpose", "reference_material")
        final_sl = target_service_line or proposed_rule.get("target_service_line")

        # Create the meta_rule
        execute(
            """INSERT INTO meta_rules
                  (rule_text, trigger_pattern, target_purpose, target_service_line, priority, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (final_rule_text, final_trigger, final_target, final_sl or None, priority, user.email),
        )
        access_log.log(
            action=f"meta_rule_{decision}",
            user_email=user.email,
            target=str(queue_id),
            ip_address=client_ip(request), user_agent=client_ua(request),
        )
    else:
        access_log.log(
            action="meta_rule_skip",
            user_email=user.email,
            target=str(queue_id),
            ip_address=client_ip(request), user_agent=client_ua(request),
        )

    # Clear the pending rule review marker
    execute(
        "UPDATE teaching_queue SET humility_articulation = NULL WHERE id = ?",
        (queue_id,),
    )

    # Finalize the queue with the user-confirmed purpose
    try:
        # Re-read queue
        q_row = fetch_one("SELECT * FROM teaching_queue WHERE id=?", (queue_id,))
        # Resolve confirmed purpose:
        # - accept/edit: use the meta-rule target (user approved)
        # - skip: use the user's original correction from the confirm step
        #   (stored in payload under pending_rule_review.rule.target_purpose)
        if decision in ("accept", "edit"):
            confirmed = final_target
        else:
            # Skip — honor the user's classification, not Anika's original guess
            try:
                payload = _json.loads(q_row.get("humility_articulation") or "{}")
                proposed_rule = payload.get("pending_rule_review", {}).get("rule", {})
                confirmed = proposed_rule.get("target_purpose") or q_row.get("anika_proposed_purpose") or "reference_material"
            except Exception:
                confirmed = q_row.get("anika_proposed_purpose") or "reference_material"
        await teaching.finalize_with_purpose(
            queue_id,
            confirmed_purpose=confirmed,
            service_line=final_sl if decision in ("accept", "edit") else None,
            created_by=user.email,
        )
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"finalize failed: {e}"}, status_code=500)

    return RedirectResponse("/train", status_code=303)


# --- Clarifications --------------------------------------------------------


@router.post("/train/clarify/{clar_id}")
async def train_clarify(
    request: Request,
    clar_id: int,
    answer: str = Form(...),
    user: User = Depends(require_user),
):
    try:
        await teaching.answer_clarification(
            clar_id, answer=answer, answered_by=user.email,
        )
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=404)
    access_log.log(
        action="teach_clarify",
        user_email=user.email, target=str(clar_id),
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train", status_code=303)


# --- Library edit / delete -------------------------------------------------


@router.post("/train/library/{entry_id}/edit")
async def train_library_edit(
    request: Request,
    entry_id: int,
    content: str = Form(...),
    kind: str = Form(...),
    scope: str = Form("universal"),
    service_line: str = Form(""),
    user: User = Depends(require_user),
):
    if kind not in ("rule", "example", "fact", "policy"):
        return JSONResponse({"ok": False, "error": "invalid kind"}, status_code=400)
    if scope not in ("universal", "service_line"):
        return JSONResponse({"ok": False, "error": "invalid scope"}, status_code=400)
    kb_library.update_entry(
        entry_id,
        content=content,
        kind=kind,
        scope=scope,
        service_line=service_line.strip() or None,
    )
    access_log.log(
        action="library_edit",
        user_email=user.email, target=str(entry_id),
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train", status_code=303)


@router.post("/train/library/{entry_id}/delete")
async def train_library_delete(
    request: Request,
    entry_id: int,
    user: User = Depends(require_user),
):
    """Soft delete — both roles can do it (consistent with the brief)."""
    ok = kb_library.soft_delete_entry(entry_id, deleted_by=user.email)
    if not ok:
        return JSONResponse({"ok": False, "error": "entry not found"}, status_code=404)
    access_log.log(
        action="library_delete",
        user_email=user.email, target=str(entry_id),
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train", status_code=303)


# --- Phase 1C-2: pattern lifecycle ----------------------------------------


@router.post("/train/patterns/{pattern_id}/dismiss")
async def train_pattern_dismiss(
    request: Request,
    pattern_id: int,
    user: User = Depends(require_user),
):
    from app.cognitive.pattern_miner import dismiss
    try:
        dismiss(pattern_id, decided_by=user.email)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=404)
    access_log.log(
        action="pattern_dismiss",
        user_email=user.email, target=str(pattern_id),
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train", status_code=303)


@router.post("/train/patterns/{pattern_id}/promote")
async def train_pattern_promote(
    request: Request,
    pattern_id: int,
    user: User = Depends(require_user),
):
    from app.cognitive.pattern_miner import promote
    try:
        meta_rule_id = promote(pattern_id, decided_by=user.email)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    access_log.log(
        action="pattern_promote",
        user_email=user.email,
        target=f"{pattern_id}->{meta_rule_id}",
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train", status_code=303)


# --- Library export --------------------------------------------------------


@router.get("/train/library/export")
async def train_library_export(
    request: Request,
    fmt: str = "xlsx",
    user: User = Depends(require_user),
):
    """Export the active library as xlsx (default) or json.

    Both roles can export — it's Prakasha sir's knowledge, he owns the
    ability to walk away with it.
    """
    import io
    import json as _json
    from datetime import datetime, timezone

    rows = kb_library.list_entries(include_inactive=False, limit=10_000)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M")

    access_log.log(
        action="library_export",
        user_email=user.email, target=fmt,
        ip_address=client_ip(request), user_agent=client_ua(request),
    )

    if fmt == "json":
        data = _json.dumps(rows, indent=2, ensure_ascii=False, default=str)
        return HTMLResponse(
            content=data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="anika-library-{stamp}.json"'},
        )

    # xlsx (default)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "knowledge_library"
    headers_row = ["id", "kind", "scope", "service_line", "content",
                   "confidence", "applied_count", "last_used_at", "created_by",
                   "created_at", "updated_at"]
    ws.append(headers_row)
    for r in rows:
        ws.append([r.get(h) for h in headers_row])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return HTMLResponse(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="anika-library-{stamp}.xlsx"'},
    )


# --- Drafting pause toggle (admin only) -----------------------------------


@router.post("/settings/drafting_paused")
async def toggle_drafting_paused(
    request: Request,
    turn: str = Form(...),
    user: User = Depends(require_admin),
):
    if turn == "on":
        drafting_paused.set_on()
        access_log.log(action="drafting_paused_on", user_email=user.email,
                       ip_address=client_ip(request), user_agent=client_ua(request))
    else:
        drafting_paused.set_off()
        access_log.log(action="drafting_paused_off", user_email=user.email,
                       ip_address=client_ip(request), user_agent=client_ua(request))
    return RedirectResponse("/settings", status_code=303)


# --- Signature-block hard lock --------------------------------------------
# No route mutates SIGNATURE_BLOCK. Any attempt to set a firm_knowledge
# row with key='signature_block' via a hypothetical write path returns 403.


@router.post("/settings/signature")
@router.put("/settings/signature")
@router.delete("/settings/signature")
async def signature_is_locked(request: Request, user: User = Depends(require_user)):
    """The signature block is constants-only. See app/config/firm_identity.py."""
    raise HTTPException(
        status_code=403,
        detail="signature block is locked; edit app/config/firm_identity.py and redeploy",
    )

# --- Meta-rules management (Phase 1B extension) ---------------------------


@router.get("/train/rules", response_class=HTMLResponse)
async def train_rules_list(request: Request, user: User = Depends(require_user)):
    """List all active meta-rules with edit/delete actions."""
    rules = fetch_all("""
        SELECT id, rule_text, trigger_pattern, target_purpose, target_service_line,
               priority, applied_count, created_by, created_at, updated_at
          FROM meta_rules
         WHERE is_active = 1
         ORDER BY priority DESC, created_at DESC
    """)
    ctx = _common_context(request, user)
    ctx.update({
        "rules": [dict(r) for r in rules],
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "rules.html", ctx)


@router.get("/train/rules/new", response_class=HTMLResponse)
async def train_rules_new_form(request: Request, user: User = Depends(require_user)):
    """Blank form to author a new meta-rule from scratch."""
    ctx = _common_context(request, user)
    ctx.update({
        "rule": None,  # template treats this as new-mode
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "rule_form.html", ctx)


@router.get("/train/rules/{rule_id}/edit", response_class=HTMLResponse)
async def train_rules_edit_form(
    request: Request,
    rule_id: int,
    user: User = Depends(require_user),
):
    """Edit an existing meta-rule."""
    row = fetch_one("SELECT * FROM meta_rules WHERE id = ? AND is_active = 1", (rule_id,))
    if not row:
        raise HTTPException(status_code=404, detail="rule not found")
    ctx = _common_context(request, user)
    ctx.update({
        "rule": dict(row),
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "rule_form.html", ctx)


@router.post("/train/rules/save")
async def train_rules_save(
    request: Request,
    rule_id: int = Form(0),   # 0 = new; >0 = edit existing
    rule_text: str = Form(...),
    trigger_pattern: str = Form(...),
    target_purpose: str = Form(...),
    target_service_line: str = Form(""),
    priority: int = Form(0),
    user: User = Depends(require_user),
):
    """Create or update a meta-rule."""
    valid_purposes = [
        "voice_example", "classifier_example", "document_type",
        "question_template", "workflow_rule", "firm_fact",
        "firm_policy", "reference_material",
    ]
    if target_purpose not in valid_purposes:
        return JSONResponse({"ok": False, "error": f"invalid purpose: {target_purpose}"}, status_code=400)

    sl = target_service_line.strip() or None

    if rule_id and rule_id > 0:
        # Update
        execute(
            """UPDATE meta_rules SET
                  rule_text = ?, trigger_pattern = ?,
                  target_purpose = ?, target_service_line = ?,
                  priority = ?
               WHERE id = ? AND is_active = 1""",
            (rule_text, trigger_pattern, target_purpose, sl, priority, rule_id),
        )
        action = f"rule_updated:{rule_id}"
    else:
        # Create new
        cur = execute(
            """INSERT INTO meta_rules
                  (rule_text, trigger_pattern, target_purpose, target_service_line, priority, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rule_text, trigger_pattern, target_purpose, sl, priority, user.email),
        )
        action = f"rule_created:{cur.lastrowid}"

    access_log.log(
        action=action, user_email=user.email,
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train/rules", status_code=303)


@router.post("/train/rules/{rule_id}/delete")
async def train_rules_delete(
    request: Request,
    rule_id: int,
    user: User = Depends(require_user),
):
    """Soft-delete a meta-rule."""
    row = fetch_one("SELECT id FROM meta_rules WHERE id = ? AND is_active = 1", (rule_id,))
    if not row:
        return JSONResponse({"ok": False, "error": "rule not found"}, status_code=404)

    execute(
        """UPDATE meta_rules SET
              is_active = 0,
              deleted_by = ?,
              deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
           WHERE id = ?""",
        (user.email, rule_id),
    )
    access_log.log(
        action=f"rule_deleted:{rule_id}", user_email=user.email,
        ip_address=client_ip(request), user_agent=client_ua(request),
    )
    return RedirectResponse("/train/rules", status_code=303)

# --- Teaching Dashboard (Phase 1B) -----------------------------------------


@router.get("/teaching-dashboard", response_class=HTMLResponse)
async def teaching_dashboard(request: Request, user: User = Depends(require_user)):
    """Prakasha sir's teaching co-pilot.

    Answers: what has he taught, how fast, where are gaps, what to teach next.
    """
    # Section 1 — Hero metrics
    total_entries = fetch_one("SELECT COUNT(*) n FROM knowledge_library WHERE is_active=1")["n"]
    total_rules = fetch_one("SELECT COUNT(*) n FROM meta_rules WHERE is_active=1")["n"]

    # Accuracy: where anika_proposed == user_confirmed (only for entries with both)
    accuracy_row = fetch_one("""
        SELECT
            SUM(CASE WHEN anika_proposed_purpose = user_confirmed_purpose THEN 1 ELSE 0 END) matches,
            COUNT(*) total
          FROM knowledge_library
         WHERE is_active=1
           AND anika_proposed_purpose IS NOT NULL
           AND user_confirmed_purpose IS NOT NULL
    """)
    accuracy_pct = 0.0
    if accuracy_row and accuracy_row["total"] and accuracy_row["total"] > 0:
        accuracy_pct = round(100.0 * (accuracy_row["matches"] or 0) / accuracy_row["total"], 1)

    # Section 2 — Teaching momentum (7d and 30d)
    week_added = fetch_one("""
        SELECT COUNT(*) n FROM knowledge_library
         WHERE is_active=1
           AND created_at > datetime('now', '-7 days')
    """)["n"]
    month_added = fetch_one("""
        SELECT COUNT(*) n FROM knowledge_library
         WHERE is_active=1
           AND created_at > datetime('now', '-30 days')
    """)["n"]

    # Section 3 — Coverage matrix (purpose x service_line)
    # Collect all service lines that appear at least once
    sl_rows = fetch_all("""
        SELECT DISTINCT COALESCE(service_line, '_universal') sl
          FROM knowledge_library WHERE is_active=1
         ORDER BY sl
    """)
    service_lines = [r["sl"] for r in sl_rows]
    purposes = [
        "voice_example", "classifier_example", "document_type",
        "question_template", "workflow_rule", "firm_fact",
        "firm_policy", "reference_material",
    ]
    matrix_rows = fetch_all("""
        SELECT purpose, COALESCE(service_line, '_universal') sl, COUNT(*) n
          FROM knowledge_library WHERE is_active=1
         GROUP BY purpose, sl
    """)
    coverage = {(r["purpose"], r["sl"]): r["n"] for r in matrix_rows}

    # Section 4 — Service line health
    service_health = []
    for sl in service_lines:
        if sl == "_universal":
            continue
        sl_total = sum(coverage.get((p, sl), 0) for p in purposes)
        missing = [p for p in ["voice_example", "workflow_rule", "question_template", "firm_fact"]
                   if coverage.get((p, sl), 0) == 0]
        score = max(0, 100 - (len(missing) * 25))  # 0-100 score
        service_health.append({
            "service": sl,
            "total_entries": sl_total,
            "missing_purposes": missing,
            "score": score,
        })

    # Section 5 — Top applied entries
    top_entries = fetch_all("""
        SELECT id, purpose, service_line, applied_count, content
          FROM knowledge_library
         WHERE is_active=1 AND applied_count > 0
         ORDER BY applied_count DESC
         LIMIT 10
    """)

    # Section 6 — Orphans (0 applied_count, older than 14 days)
    orphans = fetch_all("""
        SELECT id, purpose, service_line, content, created_at
          FROM knowledge_library
         WHERE is_active=1
           AND applied_count = 0
           AND created_at < datetime('now', '-14 days')
         ORDER BY created_at ASC
         LIMIT 10
    """)

    # Section 7 — Gap suggestions
    # "Core" purposes Drafter uses: voice_example, firm_policy, firm_fact, question_template, workflow_rule
    # Universal gaps
    gap_suggestions = []
    for p in ["voice_example", "firm_policy", "firm_fact"]:
        total_for_purpose = sum(coverage.get((p, sl), 0) for sl in service_lines)
        if total_for_purpose == 0:
            gap_suggestions.append({
                "severity": "critical",
                "message": f"No {p} entries yet anywhere. Anika can't draft authentically without these.",
            })
        elif total_for_purpose < 3:
            gap_suggestions.append({
                "severity": "warning",
                "message": f"Only {total_for_purpose} {p} entries total. Add more to improve draft quality.",
            })

    # Service line specific gaps
    for h in service_health:
        if h["missing_purposes"]:
            gap_suggestions.append({
                "severity": "info",
                "message": f"For {h['service']}: missing {', '.join(h['missing_purposes'])}.",
            })

    ctx = _common_context(request, user)
    ctx.update({
        "total_entries": total_entries,
        "total_rules": total_rules,
        "accuracy_pct": accuracy_pct,
        "accuracy_total": accuracy_row["total"] if accuracy_row else 0,
        "week_added": week_added,
        "month_added": month_added,
        "purposes": purposes,
        "service_lines": service_lines,
        "coverage": coverage,
        "service_health": service_health,
        "top_entries": [dict(r) for r in top_entries],
        "orphans": [dict(r) for r in orphans],
        "gap_suggestions": gap_suggestions,
        "active_tab": "teaching-dashboard",
    })
    return templates.TemplateResponse(request, "teaching_dashboard.html", ctx)


# --- Knowledge Graph (Phase 1B) --------------------------------------------


@router.get("/knowledge-graph", response_class=HTMLResponse)
async def knowledge_graph(request: Request, user: User = Depends(require_user)):
    """Visual network of library entries showing connections via embedding similarity."""
    import json as _json
    import math
    import struct

    from app.db import EMBEDDING_DIM

    # Fetch all active entries with content
    entries = fetch_all("""
        SELECT id, purpose, service_line, content, applied_count, kind
          FROM knowledge_library
         WHERE is_active = 1
         ORDER BY id
    """)
    entries = [dict(e) for e in entries]

    # Read pre-computed embeddings from knowledge_library_vec instead of
    # re-embedding on every page load. Each entry's embedding was stored
    # at add_entry() time as packed float32 LE bytes (see
    # app/cognitive/library.py:_pack_vector); unpack once and use. This
    # drops the page from ~N sync OpenAI calls (~2s each → ~60s total)
    # to a single SELECT plus in-memory unpack.
    vec_rows = fetch_all("""
        SELECT v.library_id AS id, v.embedding AS blob
          FROM knowledge_library_vec v
          JOIN knowledge_library k ON k.id = v.library_id
         WHERE k.is_active = 1
    """)
    embeddings = {}
    for r in vec_rows:
        try:
            blob = r["blob"]
            if not blob:
                continue
            embeddings[r["id"]] = list(struct.unpack(f"{EMBEDDING_DIM}f", blob))
        except Exception:
            continue

    # Compute similarity matrix — edge if cosine similarity > 0.6
    def cosine(a, b):
        dot = sum(x*y for x, y in zip(a, b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    edges = []
    ids = list(embeddings.keys())
    for i, aid in enumerate(ids):
        for bid in ids[i+1:]:
            sim = cosine(embeddings[aid], embeddings[bid])
            if sim > 0.6:
                edges.append({"from": aid, "to": bid, "weight": round(sim, 3)})

    # Compute node positions using simple force-directed layout
    # Place nodes in a circle initially, then iterate
    import random
    random.seed(42)
    n = len(entries)
    positions = {}
    if n > 0:
        for i, e in enumerate(entries):
            angle = 2 * math.pi * i / n
            positions[e["id"]] = {"x": 400 + 280 * math.cos(angle), "y": 300 + 250 * math.sin(angle)}

    # Simple spring layout — 100 iterations
    edge_set = {(e["from"], e["to"]): e["weight"] for e in edges}
    for _ in range(100):
        forces = {eid: {"fx": 0.0, "fy": 0.0} for eid in positions}

        # Repulsive force between all pairs
        node_ids = list(positions.keys())
        for i, a in enumerate(node_ids):
            for b in node_ids[i+1:]:
                dx = positions[a]["x"] - positions[b]["x"]
                dy = positions[a]["y"] - positions[b]["y"]
                dist = max(10, math.sqrt(dx*dx + dy*dy))
                # Repulsion ~ 1/dist^2, scaled
                rep = 4000 / (dist * dist)
                forces[a]["fx"] += rep * dx / dist
                forces[a]["fy"] += rep * dy / dist
                forces[b]["fx"] -= rep * dx / dist
                forces[b]["fy"] -= rep * dy / dist

        # Attractive force along edges
        for edge in edges:
            a, b = edge["from"], edge["to"]
            if a not in positions or b not in positions:
                continue
            dx = positions[a]["x"] - positions[b]["x"]
            dy = positions[a]["y"] - positions[b]["y"]
            dist = max(10, math.sqrt(dx*dx + dy*dy))
            # Attraction ~ dist * weight
            att = 0.02 * dist * edge["weight"]
            forces[a]["fx"] -= att * dx / dist
            forces[a]["fy"] -= att * dy / dist
            forces[b]["fx"] += att * dx / dist
            forces[b]["fy"] += att * dy / dist

        # Apply forces (damped)
        for eid in positions:
            positions[eid]["x"] += forces[eid]["fx"] * 0.1
            positions[eid]["y"] += forces[eid]["fy"] * 0.1
            # Keep within viewport
            positions[eid]["x"] = max(50, min(750, positions[eid]["x"]))
            positions[eid]["y"] = max(50, min(550, positions[eid]["y"]))

    # Prepare nodes for template
    purpose_colors = {
        "voice_example": "#8B5CF6",       # purple
        "classifier_example": "#06B6D4",  # cyan
        "document_type": "#F59E0B",       # amber
        "question_template": "#6366F1",   # indigo
        "workflow_rule": "#F97316",       # orange
        "firm_fact": "#10B981",           # emerald
        "firm_policy": "#3B82F6",         # blue
        "reference_material": "#64748B",  # slate
    }

    nodes = []
    for e in entries:
        pos = positions.get(e["id"], {"x": 400, "y": 300})
        size = 8 + min(12, e["applied_count"] * 2)  # 8-20 px based on usage
        nodes.append({
            "id": e["id"],
            "x": round(pos["x"], 1),
            "y": round(pos["y"], 1),
            "purpose": e["purpose"],
            "service_line": e["service_line"],
            "content_preview": (e["content"] or "")[:120],
            "applied_count": e["applied_count"],
            "color": purpose_colors.get(e["purpose"], "#64748B"),
            "size": size,
        })

    # Stats for the header
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "isolated": len([n for n in nodes if not any(n["id"] in (e["from"], e["to"]) for e in edges)]),
        "densest_purpose": None,
    }
    # Which purpose has most edges
    purpose_edge_count = {}
    node_by_id = {n["id"]: n for n in nodes}
    for edge in edges:
        a = node_by_id.get(edge["from"])
        b = node_by_id.get(edge["to"])
        if a and b and a["purpose"] == b["purpose"]:
            purpose_edge_count[a["purpose"]] = purpose_edge_count.get(a["purpose"], 0) + 1
    if purpose_edge_count:
        stats["densest_purpose"] = max(purpose_edge_count.items(), key=lambda x: x[1])[0]

    ctx = _common_context(request, user)
    ctx.update({
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "purpose_colors": purpose_colors,
        "active_tab": "teaching-dashboard",
    })
    return templates.TemplateResponse(request, "knowledge_graph.html", ctx)











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
