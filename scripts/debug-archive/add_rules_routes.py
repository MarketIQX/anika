from pathlib import Path
import re

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# Add the rules management routes at the end of the file (before any other trailing routes)
# We insert after /settings/signature endpoint
marker = "signature block is locked; edit app/config/firm_identity.py and redeploy"
marker_end = code.find(marker)
if marker_end == -1:
    print("Marker not found — bailing")
else:
    # Find the end of the signature route (next blank line after the HTTPException)
    insertion_point = code.find('\n\n\n', marker_end)
    if insertion_point == -1:
        insertion_point = code.find('\n\n@router', marker_end)

    NEW_ROUTES = '''

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


'''

    code = code[:insertion_point] + NEW_ROUTES + code[insertion_point:]
    p.write_text(code, encoding="utf-8")
    print(f"Added rule-management routes. New file size: {len(code)}")

# Verify import
import sys
for mod in list(sys.modules):
    if "app.dashboard" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.dashboard import routes as _r
    print("Routes import clean")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
