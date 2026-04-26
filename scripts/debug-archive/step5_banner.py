from pathlib import Path

# ============================================================
# Part 1 — Add banner to draft_detail.html
# ============================================================
p = Path("app/dashboard/templates/draft_detail.html")
code = p.read_text(encoding="utf-8")

# Inject banner right after the flash messages block, before the "Back to pending" link
OLD = '''<div class="mb-2 text-sm"><a class="underline text-slate-600" href="/drafts">← Back to pending</a></div>'''

NEW = '''<div class="mb-2 text-sm"><a class="underline text-slate-600" href="/drafts">← Back to pending</a></div>

{# ---------- Cognitive state banner (Phase 1B+) ---------- #}
{% if draft.cognitive_state == 'cold_start' %}
  <div class="mb-4 p-4 rounded-lg border-l-4 border-amber-500 bg-amber-50">
    <div class="flex items-start gap-3">
      <span class="text-amber-600 text-xl leading-none mt-0.5">⚠</span>
      <div class="flex-1">
        <div class="font-semibold text-amber-900 mb-1">
          Anika note — cold start on {{ draft.likely_service_line or 'this service line' }}
        </div>
        <div class="text-sm text-amber-800 mb-2">
          I have <strong>no learned voice examples</strong> for this service line yet.
          This draft is my best-guess, conservative interpretation — not your actual voice.
        </div>
        <div class="text-sm text-amber-800">
          <strong>What to do:</strong> edit this reply the way you would actually send it, then approve.
          Your edit becomes my first voice example for {{ draft.likely_service_line or 'this service line' }}.
          Future drafts in this area will learn from it.
        </div>
      </div>
    </div>
  </div>
{% elif draft.cognitive_state == 'learning' %}
  <div class="mb-4 p-3 rounded-lg border-l-4 border-blue-400 bg-blue-50">
    <div class="flex items-start gap-3">
      <span class="text-blue-600 text-base leading-none mt-0.5">ⓘ</span>
      <div class="text-sm text-blue-900">
        Anika note: Still learning this area — I have <strong>{{ draft.voice_coverage_count }} voice example{{ 's' if draft.voice_coverage_count != 1 else '' }}</strong>
        for {{ draft.likely_service_line or 'this service line' }}. Please review carefully; each edit sharpens my voice.
      </div>
    </div>
  </div>
{% elif draft.cognitive_state == 'learned' %}
  <div class="mb-4 p-2 rounded-lg bg-emerald-50 text-xs text-emerald-800">
    ✓ Anika is confident on {{ draft.likely_service_line or 'this service line' }} — {{ draft.voice_coverage_count }} voice examples available.
  </div>
{% endif %}'''

if NEW[:80] in code:
    print("Banner already present in template")
elif OLD in code:
    code = code.replace(OLD, NEW, 1)
    p.write_text(code, encoding="utf-8")
    print(f"Added cognitive state banner to draft_detail.html. New size: {len(code)} chars")
else:
    print("OLD marker not found. Showing what's there:")
    idx = code.find("Back to pending")
    if idx >= 0:
        print(code[max(0,idx-100):idx+200])

# ============================================================
# Part 2 — Make sure the /drafts/{id} route passes cognitive_state
# ============================================================
r = Path("app/dashboard/routes.py")
rcode = r.read_text(encoding="utf-8")

# Find the route function
import re
m = re.search(r'async def draft_detail.*?(?=\nasync def |\n@router)', rcode, re.DOTALL)
if m:
    fn_body = m.group()
    print()
    print("draft_detail route found. Check if SQL selects cognitive_state:")
    has_col = "cognitive_state" in fn_body
    print(f"  Selects cognitive_state: {has_col}")

    if not has_col:
        # Typical pattern: SELECT d.* FROM drafts d ... — if it uses d.* already, we're fine
        if "d.*" in fn_body or "drafts d" in fn_body and "SELECT *" in fn_body:
            print("  Uses SELECT * — new columns auto-included, no patch needed")
        else:
            print("  NEEDS PATCH — SQL does not SELECT cognitive_state")
            # Show the SELECT clause so I can fix it
            sel_match = re.search(r"SELECT\s+(.*?)\s+FROM", fn_body, re.DOTALL)
            if sel_match:
                print(f"  Current SELECT clause:\n  {sel_match.group()[:600]}")

# Check if any explicit column list excludes cognitive_state
# Show the SELECT clause around draft_detail
sel_idx = rcode.find("async def draft_detail")
if sel_idx >= 0:
    # Show the first 60 lines of the function
    chunk = rcode[sel_idx:sel_idx+2000]
    print()
    print("First 2000 chars of draft_detail route:")
    print("-" * 80)
    print(chunk)
