from pathlib import Path
p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# Fix the confirmed-purpose resolution in the review-rule decide endpoint
OLD = '''        # Re-read queue to get user_confirmed_purpose from Phase 1B flow
        q_row = fetch_one("SELECT * FROM teaching_queue WHERE id=?", (queue_id,))
        # Use target_purpose from the meta_rule we just saved as confirmed purpose
        confirmed = final_target if decision in ("accept", "edit") else (q_row.get("anika_proposed_purpose") or "reference_material")'''

NEW = '''        # Re-read queue
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
                confirmed = q_row.get("anika_proposed_purpose") or "reference_material"'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Fixed skip-path to honor user's correction")
else:
    print("Pattern not found")

import sys
for mod in list(sys.modules):
    if "app.dashboard" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.dashboard import routes as _r
print("Routes import clean")
