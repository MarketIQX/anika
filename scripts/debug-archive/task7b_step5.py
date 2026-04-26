from pathlib import Path
import re

# ============================================================
# PART 1 — Update the /train route to fetch awaiting_confirmation rows
# ============================================================
routes = Path("app/dashboard/routes.py")
routes_code = routes.read_text(encoding="utf-8")

# Find the /train GET handler - look for the context building
# We'll add pending_proposals fetch right after the existing fetches
marker = "clarifications = teaching.pending_clarifications()"
if marker in routes_code and "pending_proposals = fetch_all" not in routes_code:
    new_block = marker + """
    # Phase 1B — pending purpose proposals awaiting Prakash sir's confirmation
    import json as _json
    _raw_proposals = fetch_all(\"\"\"
        SELECT id, raw_content, source_type, original_filename, created_at,
               anika_proposed_purpose, anika_proposed_confidence,
               anika_reasoning, anika_suggested_sl, anika_suggested_custom,
               humility_articulation
          FROM teaching_queue
         WHERE awaiting_confirmation = 1
           AND anika_proposed_purpose IS NOT NULL
         ORDER BY created_at DESC
         LIMIT 10
    \"\"\")
    pending_proposals = []
    for p in _raw_proposals:
        p_dict = dict(p)
        # Parse the humility JSON if present
        h = p_dict.get("humility_articulation")
        if h:
            try:
                parsed = _json.loads(h)
                if "noticed_features" in parsed:
                    p_dict["humility"] = parsed
                else:
                    p_dict["humility"] = None
            except Exception:
                p_dict["humility"] = None
        else:
            p_dict["humility"] = None
        pending_proposals.append(p_dict)"""
    routes_code = routes_code.replace(marker, new_block)
    print("Added pending_proposals fetch to /train route")
else:
    if "pending_proposals" in routes_code:
        print("pending_proposals already in code - skipping route update")
    else:
        print("WARNING: Could not find marker to inject pending_proposals fetch")

# Add pending_proposals to the context dict
ctx_marker = 'ctx.update({\n        "clarifications": clarifications,'
if ctx_marker in routes_code and '"pending_proposals":' not in routes_code:
    new_ctx = 'ctx.update({\n        "pending_proposals": pending_proposals,\n        "clarifications": clarifications,'
    routes_code = routes_code.replace(ctx_marker, new_ctx)
    print("Added pending_proposals to /train template context")
elif '"pending_proposals":' in routes_code:
    print("pending_proposals already in context - skipping")

routes.write_text(routes_code, encoding="utf-8")

# ============================================================
# PART 2 — Add the pending-proposals section to train.html
# ============================================================
train_html = Path("app/dashboard/templates/train.html")
html_code = train_html.read_text(encoding="utf-8")

SECTION_MARKER = "<!-- ======================================================================\n     Section A"

NEW_SECTION_ZERO = """<!-- ======================================================================
     Section 0 — Awaiting your confirmation (Phase 1B)
     ====================================================================== -->

{% if pending_proposals %}
<section class="mb-8">
  <h2 class="text-lg font-semibold mb-3">
    Awaiting your confirmation <span class="text-sm font-normal text-slate-500">({{ pending_proposals|length }})</span>
  </h2>
  <p class="text-sm text-slate-600 mb-4">
    I looked at what you uploaded and made a best guess. Confirm if I got it right, or correct me — I'll learn from the correction.
  </p>

  <div class="space-y-4">
    {% for p in pending_proposals %}
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <div class="flex items-start justify-between mb-3">
          <div class="text-xs text-slate-500 uppercase tracking-wide">
            Upload #{{ p.id }}{% if p.original_filename %} · {{ p.original_filename }}{% endif %}
          </div>
          <span class="text-xs px-2 py-0.5 rounded
            {% if p.anika_proposed_confidence >= 0.8 %}bg-emerald-100 text-emerald-800
            {% elif p.anika_proposed_confidence >= 0.5 %}bg-amber-100 text-amber-800
            {% else %}bg-rose-100 text-rose-800{% endif %}">
            {{ "%.0f"|format(p.anika_proposed_confidence * 100) }}% confident
          </span>
        </div>

        <details class="mb-3">
          <summary class="text-xs text-slate-500 cursor-pointer">Content preview</summary>
          <pre class="mt-2 p-2 bg-slate-50 border border-slate-200 rounded text-xs whitespace-pre-wrap font-sans">{{ p.raw_content[:400] }}{% if p.raw_content|length > 400 %}…{% endif %}</pre>
        </details>

        <div class="mb-4 p-3 bg-slate-50 rounded">
          <div class="text-xs text-slate-600 mb-1">🤖 Anika's proposal:</div>
          <div class="text-sm text-slate-900 font-medium mb-1">{{ p.anika_proposed_purpose }}</div>
          <div class="text-xs text-slate-600">{{ p.anika_reasoning }}</div>
        </div>

        {% if p.humility %}
          <div class="mb-4 p-3 bg-amber-50 border border-amber-200 rounded">
            <div class="text-xs font-semibold text-amber-900 mb-2">Anika is not fully sure:</div>
            <div class="text-xs text-amber-800 mb-2"><strong>What I noticed:</strong></div>
            <ul class="text-xs text-amber-800 list-disc list-inside mb-2">
              {% for f in p.humility.noticed_features %}
                <li>{{ f }}</li>
              {% endfor %}
            </ul>
            <div class="text-xs text-amber-800 mb-2"><strong>What confuses me:</strong> {{ p.humility.uncertainty_source }}</div>
            <div class="text-xs text-amber-900 font-medium">Question: {{ p.humility.single_focused_question }}</div>
          </div>
        {% endif %}

        <form method="post" action="/train/teach/confirm" class="space-y-3">
          <input type="hidden" name="queue_id" value="{{ p.id }}" />

          <div>
            <label class="block text-xs font-medium text-slate-700 mb-2">Your answer — which purpose?</label>
            <div class="grid grid-cols-2 gap-2 text-sm">
              {% for pp in ['voice_example','classifier_example','document_type','question_template','workflow_rule','firm_fact','firm_policy','reference_material'] %}
                <label class="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded cursor-pointer hover:bg-slate-50
                  {% if pp == p.anika_proposed_purpose %}bg-slate-100 border-slate-400{% endif %}">
                  <input type="radio" name="confirmed_purpose" value="{{ pp }}" required
                    {% if pp == p.anika_proposed_purpose %}checked{% endif %} />
                  <span>{{ pp }}</span>
                </label>
              {% endfor %}
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-slate-700 mb-1">Service line (optional)</label>
              <input type="text" name="service_line"
                value="{{ p.anika_suggested_sl or '' }}"
                class="w-full border border-slate-300 rounded px-3 py-2 text-sm"
                placeholder="nri_tax, gst_indirect, audit…" />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-700 mb-1">Custom label (optional)</label>
              <input type="text" name="custom_label"
                value="{{ p.anika_suggested_custom or '' }}"
                class="w-full border border-slate-300 rounded px-3 py-2 text-sm"
                placeholder="e.g. engagement_letter" />
            </div>
          </div>

          <div class="flex items-center gap-2 pt-2">
            <button type="submit"
              class="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded text-sm font-medium">
              Confirm
            </button>
            <span class="text-xs text-slate-500">
              If I got it wrong, pick the correct purpose — I'll ask you to confirm a learning rule next.
            </span>
          </div>
        </form>

      </div>
    {% endfor %}
  </div>
</section>

"""

if NEW_SECTION_ZERO[:100] in html_code:
    print("Section 0 already in train.html — skipping")
else:
    html_code = html_code.replace(SECTION_MARKER, NEW_SECTION_ZERO + SECTION_MARKER)
    train_html.write_text(html_code, encoding="utf-8")
    print(f"Added Section 0 to train.html. New size: {len(html_code)} chars")

# Verify everything still imports
import sys
for mod in list(sys.modules):
    if mod.startswith("app.dashboard"):
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.dashboard import routes as _r
    print()
    print("Routes module imports cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
