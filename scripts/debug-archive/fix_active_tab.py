from pathlib import Path

p = Path("app/dashboard/routes.py")
code = p.read_text(encoding="utf-8")

# Fix 1: teaching_dashboard route
OLD1 = '''    ctx.update({
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
    })'''

NEW1 = '''    ctx.update({
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
    })'''

if OLD1 in code:
    code = code.replace(OLD1, NEW1)
    print("Fixed teaching_dashboard active_tab")

# Fix 2: knowledge_graph route
OLD2 = '''    ctx.update({
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "purpose_colors": purpose_colors,
        "active_tab": "train",
    })'''

NEW2 = '''    ctx.update({
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "purpose_colors": purpose_colors,
        "active_tab": "teaching-dashboard",
    })'''

if OLD2 in code:
    code = code.replace(OLD2, NEW2)
    print("Fixed knowledge_graph active_tab")

# Fix 3: rules routes (also use "train" but should use a sub-state or just stay as "train")
# Actually leaving rules as "train" is fine since /train/rules is a sub-page of train.
# But since rules, dashboard, and graph are all under the "train" umbrella conceptually,
# we could keep them all under "train" — but the Progress TAB is separate.
#
# Cleanest: Progress tab = teaching-dashboard + knowledge-graph (learning/progress things)
#           Train tab = /train + /train/rules (teaching things)

p.write_text(code, encoding="utf-8")

# Verify
import sys
for mod in list(sys.modules):
    if "app.dashboard" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.dashboard import routes as _r
print("Routes import clean")
