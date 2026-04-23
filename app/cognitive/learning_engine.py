"""Learning Engine — classifies Prakash sir's edits and evolves the Drafter prompt.

When Prakash sir edits a draft (instead of just tapping Send), we treat that
edit as a teaching signal. We:

1. Diff the before/after bodies to compute an edit_delta.
2. Ask a small model to categorize the edit as one of:
      - style    : voice / phrasing / tone preferences (always learnable)
      - fact     : a fact correction (learnable — note it in firm_knowledge
                   or clients)
      - context  : missing/superfluous context specific to this thread only
                   (not learnable — do NOT propagate)
      - rejection: draft was off-track; treat like an approved rejection
                   signal (update prompt to avoid recurrence)
3. If style or fact: append a delta note to the active drafter prompt and
   write a new prompt version (is_active=1 flips). Style changes are always
   worth learning; fact corrections record the corrected fact in memory.
4. Log the whole thing to reasoning_log.

Why a separate cognitive module: this is orthogonal to request-time agents;
it runs after approval events and is only read by the Drafter at draft
time (via the active prompt row).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from openai import OpenAI

from app.cognitive import reasoning_log
from app.config import get_settings
from app.db import execute, fetch_all, fetch_one
from app.tools import memory_tool

logger = logging.getLogger(__name__)


EDIT_CATEGORIES = ("style", "fact", "context", "rejection")


@dataclass
class EditClassification:
    category: str
    rationale: str
    extracted_fact: str | None = None  # populated when category == 'fact'
    style_rule: str | None = None      # populated when category == 'style'


def _openai() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)


def compute_delta(before: str, after: str) -> dict[str, Any]:
    """Return a structured diff between two plain-text bodies.

    Shape:
      {
        "before": "...",
        "after":  "...",
        "similarity": 0.0..1.0,
        "changes": [{"op": "replace"|"insert"|"delete", "before": "...", "after": "..."}, ...]
      }
    similarity uses difflib.SequenceMatcher — cheap and good enough to know
    "substantial rewrite vs light tweak".
    """
    sm = SequenceMatcher(None, before or "", after or "")
    changes: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        changes.append(
            {
                "op": tag,
                "before": (before or "")[i1:i2],
                "after": (after or "")[j1:j2],
            }
        )
    return {
        "before": before,
        "after": after,
        "similarity": round(sm.ratio(), 4),
        "changes": changes,
    }


_CLASSIFIER_PROMPT = """You are Anika's Learning Engine. Prakash sir just edited a draft you generated.

Your job: classify his edit so that only *generalizable* lessons update the
Drafter prompt, and thread-specific edits are ignored.

Categories (choose exactly one):
- style     : voice, phrasing, tone, salutation, sign-off, formality. Always
              generalizable — update the Drafter prompt.
- fact      : a factual correction about the firm, a client, a service, a
              phone number, a partner's specialty. Capture the corrected fact
              so future drafts use it.
- context   : he added or removed content that is SPECIFIC to this one
              enquiry (e.g. a past-engagement reference that only applies to
              this sender). NOT generalizable.
- rejection : the draft was on the wrong topic / he effectively replaced it.
              Treat as a signal to avoid a repeat in future drafts of this
              class.

Return strict JSON:
{
  "category": "style|fact|context|rejection",
  "rationale": "one short sentence",
  "extracted_fact": "the corrected fact, if category=fact; otherwise null",
  "style_rule": "the imperative rule to add to the Drafter prompt, if category=style; otherwise null"
}
"""


def classify_edit(
    original_body: str,
    edited_body: str,
    edit_instruction: str | None = None,
) -> EditClassification:
    """Call the learner model to categorize an edit.

    edit_instruction is Prakash sir's natural-language request ("make it more
    formal", "mention MSI"); when present it's usually the strongest signal.
    """
    user_payload = {
        "original_body": original_body,
        "edited_body": edited_body,
        "edit_instruction": edit_instruction or "",
    }
    s = get_settings()
    client = _openai()
    resp = client.chat.completions.create(
        model=s.openai_model_learner,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _CLASSIFIER_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    cat = data.get("category", "context")
    if cat not in EDIT_CATEGORIES:
        cat = "context"
    return EditClassification(
        category=cat,
        rationale=data.get("rationale", ""),
        extracted_fact=data.get("extracted_fact"),
        style_rule=data.get("style_rule"),
    )


def _active_prompt(agent: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT id, version, prompt_text FROM agent_prompts
         WHERE agent_name = ? AND is_active = 1
         ORDER BY version DESC LIMIT 1
        """,
        (agent,),
    )


def _deactivate_prompts(agent: str) -> None:
    execute("UPDATE agent_prompts SET is_active=0 WHERE agent_name=?", (agent,))


def evolve_drafter_prompt(style_rule: str, change_note: str) -> int:
    """Append a new style rule to the Drafter prompt as a new active version.

    Why a new row rather than editing in place: we want a full audit trail of
    every prompt mutation, so we can roll back and so the dashboard can show
    "Prompt v7 → v8 added rule: …".
    """
    current = _active_prompt("drafter")
    if current:
        base = current["prompt_text"].rstrip()
        new_text = f"{base}\n\nLearned rule ({change_note}): {style_rule.strip()}"
        new_version = int(current["version"]) + 1
    else:
        new_text = f"Learned rule ({change_note}): {style_rule.strip()}"
        new_version = 1

    _deactivate_prompts("drafter")
    cur = execute(
        """
        INSERT INTO agent_prompts(agent_name, version, prompt_text, change_note, is_active)
        VALUES ('drafter', ?, ?, ?, 1)
        """,
        (new_version, new_text, change_note),
    )
    return int(cur.lastrowid)


def record_corrected_fact(fact: str, source_draft_id: int | None) -> int | None:
    """Store a corrected fact as a firm_snippet memory.

    We deliberately don't overwrite firm_knowledge automatically — facts
    extracted by an LLM can be wrong. The dashboard Train tab surfaces them
    so AK can promote good ones into firm_knowledge manually.
    """
    return memory_tool.store_memory(
        kind="firm_snippet",
        content=fact,
        source_draft_id=source_draft_id,
        tags=["learner_correction"],
    )


def on_edit(
    draft_id: int,
    original_body: str,
    edited_body: str,
    edit_instruction: str | None,
    approval_id: int,
) -> dict[str, Any]:
    """Entry point — called after an 'edited' approval row lands.

    Effects:
      - writes edit_delta_json and edit_category onto the approvals row
      - may evolve the Drafter prompt (style)
      - may record a corrected-fact memory (fact)
      - logs the decision in reasoning_log
    """
    delta = compute_delta(original_body, edited_body)

    try:
        classification = classify_edit(original_body, edited_body, edit_instruction)
    except Exception as e:  # noqa: BLE001 — never let the learner crash the app
        logger.error("Edit classification failed: %s", e)
        classification = EditClassification(category="context", rationale=f"classifier_error:{e}")

    execute(
        """
        UPDATE approvals
           SET edit_category = ?,
               edit_delta_json = ?
         WHERE id = ?
        """,
        (classification.category, json.dumps(delta, ensure_ascii=False), approval_id),
    )

    actions: list[str] = []
    if classification.category == "style" and classification.style_rule:
        evolve_drafter_prompt(
            style_rule=classification.style_rule,
            change_note=f"from edit on draft #{draft_id}: {classification.rationale}",
        )
        actions.append("evolved_drafter_prompt")
    elif classification.category == "fact" and classification.extracted_fact:
        mid = record_corrected_fact(classification.extracted_fact, source_draft_id=draft_id)
        if mid is not None:
            actions.append(f"recorded_corrected_fact:{mid}")
    elif classification.category == "rejection":
        # Treat like style: warn future drafts away from this mistake.
        evolve_drafter_prompt(
            style_rule=(
                f"Avoid repeating the kind of mistake that required rejection on draft "
                f"#{draft_id}. Context: {classification.rationale}"
            ),
            change_note=f"from rejection on draft #{draft_id}",
        )
        actions.append("evolved_drafter_prompt_from_rejection")

    reasoning_log.log(
        agent_name="learner",
        input_obj={
            "draft_id": draft_id,
            "approval_id": approval_id,
            "edit_instruction": edit_instruction,
            "similarity": delta["similarity"],
        },
        output_obj={
            "category": classification.category,
            "actions": actions,
            "rationale": classification.rationale,
        },
        reasoning_text=classification.rationale,
        model=get_settings().openai_model_learner,
        draft_id=draft_id,
    )

    return {
        "category": classification.category,
        "rationale": classification.rationale,
        "actions": actions,
        "similarity": delta["similarity"],
    }


def summarise_recent_learning(limit: int = 20) -> list[dict[str, Any]]:
    """Return the last `limit` learner entries for the Train tab."""
    return fetch_all(
        """
        SELECT rl.created_at, rl.draft_id, rl.output_json, rl.reasoning_text
          FROM reasoning_log rl
         WHERE rl.agent_name = 'learner'
         ORDER BY rl.created_at DESC
         LIMIT ?
        """,
        (limit,),
    )
