from pathlib import Path

p = Path("app/dashboard/templates/draft_detail.html")
code = p.read_text(encoding="utf-8")

# Insert banner right after "Back to pending" link
anchor = '<div class="mb-2 text-sm"><a class="underline text-slate-600" href="/drafts">← Back to pending</a></div>'

banner = '''<div class="mb-2 text-sm"><a class="underline text-slate-600" href="/drafts">← Back to pending</a></div>

{# ---------- Cognitive state banner (Phase 1B+) ---------- #}
{% if draft.cognitive_state == 'cold_start' %}
  <div class="mb-4 p-4 rounded-lg border-l-4 border-amber-500 bg-amber-50">
    <div class="flex items-start gap-3">
      <span class="text-amber-600 text-xl leading-none mt-0.5">!</span>
      <div class="flex-1">
        <div class="font-semibold text-amber-900 mb-1">
          Anika note - cold start on {{ draft.likely_service_line or 'this service line' }}
        </div>
        <div class="text-sm text-amber-800 mb-2">
          I have <strong>no learned voice examples</strong> for this service line yet.
          This draft is my best-guess, conservative interpretation - not your actual voice.
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
    <div class="text-sm text-blue-900">
      Anika note: Still learning this area - I have <strong>{{ draft.voice_coverage_count }} voice example(s)</strong>
      for {{ draft.likely_service_line or 'this service line' }}. Please review carefully; each edit sharpens my voice.
    </div>
  </div>
{% elif draft.cognitive_state == 'learned' %}
  <div class="mb-4 p-2 rounded-lg bg-emerald-50 text-xs text-emerald-800">
    Anika is confident on {{ draft.likely_service_line or 'this service line' }} - {{ draft.voice_coverage_count }} voice examples available.
  </div>
{% endif %}
'''

if "cognitive_state" in code:
    print("Already has cognitive_state — refusing to double-insert")
elif anchor in code:
    code = code.replace(anchor, banner, 1)
    p.write_text(code, encoding="utf-8")
    print(f"Added banner. New file size: {len(code)} chars")
else:
    print("ANCHOR NOT FOUND — bailing")

# Verify
check = Path("app/dashboard/templates/draft_detail.html").read_text(encoding="utf-8")
print(f"Verification: 'cognitive_state' in file: {'cognitive_state' in check}")
print(f"Verification: 'cold_start' in file: {'cold_start' in check}")
