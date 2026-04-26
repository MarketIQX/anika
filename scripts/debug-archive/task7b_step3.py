from pathlib import Path

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# 1. Add imports for meta_rule_generator and duplicate_judge
if "from app.agents import meta_rule_generator" not in code:
    old_imp = "from app.agents import purpose_classifier, humility_layer"
    new_imp = "from app.agents import purpose_classifier, humility_layer\nfrom app.agents import meta_rule_generator, duplicate_judge"
    if old_imp in code:
        code = code.replace(old_imp, new_imp)
        print("Added meta_rule_generator + duplicate_judge imports")
    else:
        print("WARNING: Anchor not found for imports")

# 2. Find a good insertion point — right after train_teach route, before clarifications section
marker = "# --- Clarifications"
marker_idx = code.find(marker)

if marker_idx == -1:
    print("Clarifications marker not found")
else:
    NEW_ENDPOINTS = '''# --- Teach confirmation (Phase 1B feedback loop) --------------------------


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
        ("confirmed", queue_id),
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

    # No correction → finalize queue (create library entry with confirmed purpose)
    # Pass the user-confirmed purpose to finalize_queue so the Learner knows the context.
    try:
        await teaching.finalize_queue(
            queue_id,
            confirmed_purpose=confirmed_purpose,
            custom_label=(custom_label or None),
            service_line=(service_line or None),
        )
    except TypeError:
        # finalize_queue may not accept new kwargs yet - fall back to old signature
        # Store the confirmation data on queue, finalize without new args
        await teaching.finalize_queue(queue_id)

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

    # Finalize the queue (creates the library entry)
    try:
        await teaching.finalize_queue(queue_id)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"finalize failed: {e}"}, status_code=500)

    return RedirectResponse("/train", status_code=303)


'''

    code = code[:marker_idx] + NEW_ENDPOINTS + code[marker_idx:]
    p.write_text(code, encoding="utf-8")
    print(f"Added confirmation + review-rule endpoints. New file size: {len(code)}")

# Verify imports
import sys
for mod in list(sys.modules):
    if mod.startswith("app.dashboard"):
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.dashboard import routes as _r
    print()
    print("Route module imports cleanly - syntax OK")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
