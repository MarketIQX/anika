from pathlib import Path

template = """{% extends \"base.html\" %}
{% block title %}Rules | Anika{% endblock %}
{% block content %}

<div class=\"max-w-5xl mx-auto\">
  <div class=\"flex items-start justify-between mb-4\">
    <div>
      <h1 class=\"text-2xl font-semibold text-slate-900\">Anika's Learning Rules</h1>
      <p class=\"text-sm text-slate-600 mt-1\">
        Rules you've taught Anika. She applies these when classifying new uploads.
        Higher priority rules fire first.
      </p>
    </div>
    <div class=\"flex items-center gap-2\">
      <a href=\"/train\" class=\"text-sm text-slate-500 hover:text-slate-900 px-3 py-2\">← Back to Train</a>
      <a href=\"/train/rules/new\"
         class=\"bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded text-sm font-medium\">
        + Add new rule
      </a>
    </div>
  </div>

  {% if not rules %}
    <div class=\"bg-white border border-slate-200 rounded-lg p-8 text-center\">
      <p class=\"text-slate-600 mb-4\">No rules yet.</p>
      <p class=\"text-xs text-slate-500 mb-4\">
        Rules are created automatically when you correct Anika's classification,
        or manually by clicking \"Add new rule\" above.
      </p>
      <a href=\"/train/rules/new\"
         class=\"inline-block bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded text-sm font-medium\">
        Add your first rule
      </a>
    </div>
  {% else %}
    <div class=\"bg-white border border-slate-200 rounded-lg overflow-hidden\">
      <table class=\"w-full text-sm\">
        <thead class=\"bg-slate-50 border-b border-slate-200\">
          <tr class=\"text-left\">
            <th class=\"px-4 py-3 font-medium text-slate-700 w-12\">#</th>
            <th class=\"px-4 py-3 font-medium text-slate-700\">Rule</th>
            <th class=\"px-4 py-3 font-medium text-slate-700 w-40\">Target purpose</th>
            <th class=\"px-4 py-3 font-medium text-slate-700 w-24\">Service</th>
            <th class=\"px-4 py-3 font-medium text-slate-700 w-20 text-center\">Priority</th>
            <th class=\"px-4 py-3 font-medium text-slate-700 w-20 text-center\">Used</th>
            <th class=\"px-4 py-3 font-medium text-slate-700 w-32\">Actions</th>
          </tr>
        </thead>
        <tbody class=\"divide-y divide-slate-100\">
          {% for r in rules %}
            <tr class=\"hover:bg-slate-50\">
              <td class=\"px-4 py-3 text-slate-400 font-mono text-xs\">{{ r.id }}</td>
              <td class=\"px-4 py-3\">
                <div class=\"text-slate-900\">{{ r.rule_text[:120] }}{% if r.rule_text|length > 120 %}…{% endif %}</div>
                <div class=\"text-xs text-slate-500 mt-1\">
                  <span class=\"font-medium\">When:</span> {{ r.trigger_pattern[:100] }}{% if r.trigger_pattern and r.trigger_pattern|length > 100 %}…{% endif %}
                </div>
              </td>
              <td class=\"px-4 py-3\">
                <span class=\"inline-block px-2 py-0.5 rounded text-xs font-medium
                  {% if r.target_purpose == 'firm_policy' %}bg-blue-100 text-blue-800
                  {% elif r.target_purpose == 'firm_fact' %}bg-emerald-100 text-emerald-800
                  {% elif r.target_purpose == 'voice_example' %}bg-purple-100 text-purple-800
                  {% elif r.target_purpose == 'workflow_rule' %}bg-amber-100 text-amber-800
                  {% elif r.target_purpose == 'question_template' %}bg-indigo-100 text-indigo-800
                  {% elif r.target_purpose == 'reference_material' %}bg-slate-100 text-slate-700
                  {% else %}bg-slate-100 text-slate-700{% endif %}\">
                  {{ r.target_purpose }}
                </span>
              </td>
              <td class=\"px-4 py-3 text-slate-600 text-xs\">
                {{ r.target_service_line or '—' }}
              </td>
              <td class=\"px-4 py-3 text-center text-slate-600 font-mono text-xs\">{{ r.priority }}</td>
              <td class=\"px-4 py-3 text-center text-slate-600 font-mono text-xs\">{{ r.applied_count }}×</td>
              <td class=\"px-4 py-3\">
                <div class=\"flex items-center gap-2\">
                  <a href=\"/train/rules/{{ r.id }}/edit\"
                     class=\"text-blue-600 hover:text-blue-800 text-xs font-medium\">Edit</a>
                  <form method=\"post\" action=\"/train/rules/{{ r.id }}/delete\"
                        onsubmit=\"return confirm('Delete this rule? (soft-delete, audit preserved)');\">
                    <button type=\"submit\"
                            class=\"text-rose-600 hover:text-rose-800 text-xs font-medium\">Delete</button>
                  </form>
                </div>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class=\"mt-4 text-xs text-slate-500\">
      {{ rules|length }} active rule{% if rules|length != 1 %}s{% endif %}.
      Rules fire during classification of new uploads.
    </div>
  {% endif %}
</div>

{% endblock %}
"""

p = Path("app/dashboard/templates/rules.html")
p.write_text(template, encoding="utf-8")
print(f"Wrote rules.html ({len(template)} chars)")
