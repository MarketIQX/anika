from pathlib import Path

p = Path("app/tools/notify_tool.py")
code = p.read_text(encoding="utf-8")

# Use exact characters from the file (single backslash-n, not double)
OLD = '''    url = _draft_url(draft_id)
    tag = urgency.upper() if urgency else "NEW"
    sl = f" [{service_line}]" if service_line else ""
    subject = f"Anika: draft ready for approval ({tag}{sl})"
    body = (
        f"New enquiry summary:\n"
        f"{sender_summary.strip()}\n\n"
        f"Review & approve: {url}\n\n"
        f"— Anika"
    )'''

NEW = '''    url = _draft_url(draft_id)
    tag = urgency.upper() if urgency else "NEW"
    sl = f" [{service_line}]" if service_line else ""

    # Cognitive state — fetch from the draft row we just stored.
    from app.db import fetch_one as _fetch_one
    cog_row = _fetch_one(
        "SELECT cognitive_state, voice_coverage_count FROM drafts WHERE id = ?",
        (draft_id,),
    )
    cognitive_state = cog_row["cognitive_state"] if cog_row else None
    voice_count = cog_row["voice_coverage_count"] if cog_row else 0

    # Subject line marker — flag cold_start prominently
    cold_marker = " — TEACH ME" if cognitive_state == "cold_start" else ""
    subject = f"Anika: draft ready for approval ({tag}{sl}){cold_marker}"

    # Honesty preamble for cold_start / learning states
    if cognitive_state == "cold_start":
        honesty_preamble = (
            f"COLD START — first draft for {service_line or 'this service line'}\n\n"
            f"I have no learned voice examples for this area yet. This draft is my "
            f"best-guess, conservative interpretation — not your actual voice.\n\n"
            f"What to do: edit the draft to your actual style before approving. "
            f"Your edit becomes my first voice example for {service_line or 'this service line'}, "
            f"and future drafts in this area will learn from it.\n\n"
        )
    elif cognitive_state == "learning":
        honesty_preamble = (
            f"LEARNING — I have {voice_count} voice example(s) for "
            f"{service_line or 'this service line'}.\n"
            f"Still early in learning. Please review carefully — each edit sharpens my voice.\n\n"
        )
    else:
        honesty_preamble = ""

    body = (
        f"{honesty_preamble}"
        f"New enquiry summary:\n"
        f"{sender_summary.strip()}\n\n"
        f"Review & approve: {url}\n\n"
        f"— Anika"
    )'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Patched notify_draft_ready with cognitive state honesty")
else:
    print("OLD still not matching. Trying anchor-based replacement.")

# Verify
import sys
for mod in list(sys.modules):
    if "notify_tool" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.tools import notify_tool
print()
print("notify_tool imports cleanly")

# Show the new function start
import inspect
src = inspect.getsource(notify_tool.notify_draft_ready)
print()
print("First 1500 chars of patched function:")
print(src[:1500])
