from pathlib import Path
import re

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# Check if already added
if "/teaching-dashboard" in code or "teaching_dashboard" in code:
    print("Teaching dashboard route already present")
else:
    # Find a good insertion point — after the rules routes
    marker = '"Rule management — user-friendly CRUD over meta_rules'
    # Fallback: look for the end of any meta_rules endpoint
    if marker not in code:
        marker = "rule_deleted:"
    idx = code.find(marker)
    if idx == -1:
        # Final fallback: end of signature lock block
        idx = code.find("signature block is locked; edit")
    if idx == -1:
        print("Could not find insertion point")
    else:
        # Find the end of the containing function's closing brace/return
        # We scan for the next \n\n\n (function separator) after the marker
        end_idx = code.find("\n\n\n", idx)
        if end_idx == -1:
            end_idx = code.find("\n\n@router", idx)

        NEW_ROUTE = '''

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
        "active_tab": "train",
    })
    return templates.TemplateResponse(request, "teaching_dashboard.html", ctx)


'''
        code = code[:end_idx] + NEW_ROUTE + code[end_idx:]
        p.write_text(code, encoding="utf-8")
        print(f"Added teaching_dashboard route. File size: {len(code)}")

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
