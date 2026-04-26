from pathlib import Path

template = """{% extends "base.html" %}
{% block title %}Review rule | Anika{% endblock %}
{% block content %}

<div class="max-w-3xl mx-auto">
  <div class="mb-6">
    <a href="/train" class="text-sm text-slate-500 hover:text-slate-900">← Back to Train</a>
  </div>

  <h1 class="text-2xl font-semibold text-slate-900 mb-2">Anika learned from your correction</h1>
  <p class="text-slate-600 mb-6">
    You corrected my classification. Here's the rule I'd like to remember so I don't make the same mistake again.
    Should I save it?
  </p>

  {% if not rule_data %}
    <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900">
      No pending rule to review.
    </div>
  {% else %}

    {% set rule = rule_data.rule %}
    {% set dup = rule_data.duplicate_check %}

    {# Duplicate warning banner if judge flagged one #}
    {% if dup and dup.is_duplicate %}
      <div class="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6 rounded-r-lg">
        <div class="flex items-start gap-3">
          <span class="text-amber-600 text-xl leading-none">⚠</span>
          <div>
            <div class="font-semibold text-amber-900 mb-1">I already have a similar rule (id {{ dup.duplicate_of_id }})</div>
            <div class="text-sm text-amber-800">{{ dup.reasoning }}</div>
            {% if dup.difference_if_similar %}
              <div class="text-sm text-amber-700 mt-2"><strong>But there is a difference:</strong> {{ dup.difference_if_similar }}</div>
            {% endif %}
          </div>
        </div>
      </div>
    {% endif %}

    {# Source content preview #}
    <div class="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-6">
      <div class="text-xs uppercase tracking-wide text-slate-500 mb-2">Content you uploaded</div>
      <div class="text-sm text-slate-700 whitespace-pre-wrap">{{ queue_row.raw_content[:500] }}{% if queue_row.raw_content|length > 500 %}…{% endif %}</div>
    </div>

    {# Anika's proposed rule (editable) #}
    <form method="post" action="/train/review-rule/{{ queue_row.id }}/decide" class="space-y-4">

      <div class="bg-white border border-slate-200 rounded-lg p-6 space-y-4">
        <div class="flex items-center gap-2">
          <span class="text-lg">🤖</span>
          <span class="text-sm font-semibold text-slate-900">Anika's proposed rule</span>
          <span class="ml-auto text-xs text-slate-500">confidence: {{ "%.0f"|format(rule.confidence * 100) }}%</span>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">RULE TEXT (what I want to remember)</label>
          <textarea name="rule_text" rows="3"
            class="w-full border border-slate-300 rounded px-3 py-2 text-sm">{{ rule.rule_text }}</textarea>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">WHEN IT APPLIES</label>
          <textarea name="trigger_pattern" rows="2"
            class="w-full border border-slate-300 rounded px-3 py-2 text-sm">{{ rule.trigger_pattern }}</textarea>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">TARGET PURPOSE</label>
            <select name="target_purpose" class="w-full border border-slate-300 rounded px-3 py-2 text-sm">
              {% for p in ['voice_example','classifier_example','document_type','question_template','workflow_rule','firm_fact','firm_policy','reference_material'] %}
                <option value="{{ p }}" {% if p == rule.target_purpose %}selected{% endif %}>{{ p }}</option>
              {% endfor %}
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">SERVICE LINE (optional)</label>
            <input type="text" name="target_service_line"
              value="{{ rule.target_service_line or '' }}"
              class="w-full border border-slate-300 rounded px-3 py-2 text-sm"
              placeholder="e.g. nri_tax, audit, gst_indirect" />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">PRIORITY (higher = applies first)</label>
          <input type="number" name="priority" value="5" min="0" max="100"
            class="w-32 border border-slate-300 rounded px-3 py-2 text-sm" />
        </div>

        <details class="text-xs text-slate-500">
          <summary class="cursor-pointer">Why Anika wants this rule</summary>
          <div class="mt-2 pl-2 border-l-2 border-slate-200">{{ rule.reasoning }}</div>
        </details>
      </div>

      <div class="flex items-center gap-3">
        <button type="submit" name="decision" value="accept"
          class="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded text-sm font-medium">
          Save rule as-is
        </button>
        <button type="submit" name="decision" value="edit"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium">
          Save with my edits
        </button>
        <button type="submit" name="decision" value="skip"
          class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded text-sm font-medium">
          Skip — don't save
        </button>
      </div>

      <p class="text-xs text-slate-500">
        Either way, your correction for this specific upload is already saved. This just decides whether I remember the general pattern.
      </p>
    </form>

  {% endif %}
</div>

{% endblock %}
"""

Path("app/dashboard/templates/review_rule.html").write_text(template, encoding="utf-8")
print("Wrote app/dashboard/templates/review_rule.html")
print(f"Template size: {len(template)} chars")
