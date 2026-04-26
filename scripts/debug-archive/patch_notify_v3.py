from pathlib import Path
import re

p = Path("app/tools/notify_tool.py")
code = p.read_text(encoding="utf-8")

# Use regex with line anchors — bypass exact-match-with-escaped-chars issue
# Match from "url = _draft_url" to the closing "    )" before "    try:"
pattern = re.compile(
    r"    url = _draft_url\(draft_id\).*?    \)\n    try:",
    re.DOTALL
)

m = pattern.search(code)
if not m:
    print("Pattern not found")
else:
    old_block = m.group()
    print(f"Found block, length: {len(old_block)} chars")

    new_block = '''    url = _draft_url(draft_id)
    tag = urgency.upper() if urgency else "NEW"
    sl = f" [{service_line}]" if service_line else ""

    # Cognitive state from the draft row
    from app.db import fetch_one as _fetch_one
    cog_row = _fetch_one(
        "SELECT cognitive_state, voice_coverage_count FROM drafts WHERE id = ?",
        (draft_id,),
    )
    cognitive_state = cog_row["cognitive_state"] if cog_row else None
    voice_count = cog_row["voice_coverage_count"] if cog_row else 0

    cold_marker = " - TEACH ME" if cognitive_state == "cold_start" else ""
    subject = f"Anika: draft ready for approval ({tag}{sl}){cold_marker}"

    if cognitive_state == "cold_start":
        sl_name = service_line or "this service line"
        honesty_preamble = (
            f"COLD START - first draft for {sl_name}\\n\\n"
            f"I have no learned voice examples for this area yet. This draft is my "
            f"best-guess, conservative interpretation - not your actual voice.\\n\\n"
            f"What to do: edit the draft to your actual style before approving. "
            f"Your edit becomes my first voice example for {sl_name}, "
            f"and future drafts in this area will learn from it.\\n\\n"
        )
    elif cognitive_state == "learning":
        sl_name = service_line or "this service line"
        honesty_preamble = (
            f"LEARNING - I have {voice_count} voice example(s) for {sl_name}.\\n"
            f"Still early in learning. Please review carefully - each edit sharpens my voice.\\n\\n"
        )
    else:
        honesty_preamble = ""

    body = (
        f"{honesty_preamble}"
        f"New enquiry summary:\\n"
        f"{sender_summary.strip()}\\n\\n"
        f"Review & approve: {url}\\n\\n"
        f"- Anika"
    )
    try:'''

    code = code[:m.start()] + new_block + code[m.end():]
    p.write_text(code, encoding="utf-8")
    print("Replaced via regex anchor")

# Verify
import sys
for mod in list(sys.modules):
    if "notify_tool" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.tools import notify_tool
import inspect
src = inspect.getsource(notify_tool.notify_draft_ready)
print()
print("Patched function:")
print(src[:2500])
