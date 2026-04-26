from pathlib import Path

p = Path("app/agents/drafter.py")
code = p.read_text(encoding="utf-8")

OLD = '''    cur = execute(
        """
        INSERT INTO drafts
          (email_id, parent_draft_id, subject, body, tone_notes, uses_signature,
           sent_status, model, prompt_version, reasoning)
        VALUES (?,?,?,?,?,1,'pending_approval',?,?,?)
        """,
        (
            email_id,
            parent_draft_id,
            output.subject,
            body,
            output.tone_notes,
            get_settings().openai_model_drafter,
            None,                 # prompt_version no longer meaningful — prompt is assembled
            output.reasoning,
        ),
    )
    draft_id = int(cur.lastrowid)

    # Credit every library entry that went into this draft.
    library.bump_applied(used_ids)
    return draft_id'''

NEW = '''    cur = execute(
        """
        INSERT INTO drafts
          (email_id, parent_draft_id, subject, body, tone_notes, uses_signature,
           sent_status, model, prompt_version, reasoning,
           cognitive_state, voice_coverage_count)
        VALUES (?,?,?,?,?,1,'pending_approval',?,?,?,?,?)
        """,
        (
            email_id,
            parent_draft_id,
            output.subject,
            body,
            output.tone_notes,
            get_settings().openai_model_drafter,
            None,                 # prompt_version no longer meaningful — prompt is assembled
            output.reasoning,
            coverage.get("cognitive_state"),
            coverage.get("count", 0),
        ),
    )
    draft_id = int(cur.lastrowid)

    # Credit every library entry that went into this draft.
    library.bump_applied(used_ids)
    return draft_id'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Updated INSERT INTO drafts — now persists cognitive_state + voice_coverage_count")
else:
    print("OLD not found")

# Verify
import sys
for mod in list(sys.modules):
    if "drafter" in mod or "app.agents" in mod or "app.cognitive" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.agents import drafter
    print("drafter module imports cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
