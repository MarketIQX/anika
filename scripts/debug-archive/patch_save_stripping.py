from pathlib import Path

p = Path("app/agents/approver.py")
code = p.read_text(encoding="utf-8")

# Add signature stripping inside _save_as_voice_example
OLD = '''    body = draft_row.get("body") or ""
    if len(body) < 50:
        logger.info("skipping voice_example save for draft %s — body too short", draft_row.get("id"))
        return None

    service_line = (draft_row.get("likely_service_line") or "").strip() or None'''

NEW = '''    body = draft_row.get("body") or ""
    # Strip signature block so voice_example teaches BODY only.
    # The Drafter's own prompt + ensure_signature() append the canonical signature at draft time.
    # Never let signature text leak into voice_examples — would cause double-sig on retrieval.
    _sig_markers = (
        "\\nWarm regards,", "\\nBest regards,", "\\nYours faithfully,",
        "\\nRegards,", "\\nSincerely,",
        "\\nS V Prakasha", "\\nCA Prakasha", "\\nCA S V Prakasha",
    )
    _cut_at = len(body)
    for _m in _sig_markers:
        _idx = body.find(_m)
        if _idx >= 0 and _idx < _cut_at:
            _cut_at = _idx
    if _cut_at < len(body):
        body = body[:_cut_at].rstrip()

    if len(body) < 50:
        logger.info("skipping voice_example save for draft %s — body too short after sig strip", draft_row.get("id"))
        return None

    service_line = (draft_row.get("likely_service_line") or "").strip() or None'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Patched _save_as_voice_example to strip signatures before saving")
else:
    print("OLD block not found — checking current state...")

# Verify
check = p.read_text(encoding="utf-8")
if "_sig_markers" in check:
    print("Verified: signature-strip logic is now in approver.py")

# Import check
import sys
for mod in list(sys.modules):
    if "approver" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.agents import approver
print("approver module imports cleanly")
