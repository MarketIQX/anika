from pathlib import Path

p = Path("app/agents/approver.py")
code = p.read_text(encoding="utf-8")

# Find the approve function and inject voice-save logic
OLD = '''    sent_log_id = await sender.send_approved_draft(draft_id, approval_id)
    return {"approval_id": approval_id, "sent_log_id": sent_log_id}'''

NEW = '''    sent_log_id = await sender.send_approved_draft(draft_id, approval_id)

    # Auto-save as voice_example if this draft came from an edit chain.
    # Rationale: if Prakash sir edited a draft before approving, the final
    # approved body represents his preferred voice. Save it to knowledge_library
    # so future drafts can retrieve and mirror it.
    try:
        if row.get("parent_draft_id"):
            _save_as_voice_example(row, decided_by=decided_by)
    except Exception as e:  # noqa: BLE001
        logger.error("auto voice_example save failed for draft %s: %s", draft_id, e)

    return {"approval_id": approval_id, "sent_log_id": sent_log_id}


def _save_as_voice_example(draft_row: dict[str, Any], *, decided_by: str) -> int | None:
    """Save an approved draft (that came from an edit chain) as a voice_example.

    Called from approver.approve() when the draft has parent_draft_id — meaning
    the user edited at least once before approving. The approved body is the
    gold-standard voice for this service line.
    """
    from app.cognitive.library import add_entry
    from app.db import execute as db_execute

    body = draft_row.get("body") or ""
    if len(body) < 50:
        logger.info("skipping voice_example save for draft %s — body too short", draft_row.get("id"))
        return None

    service_line = (draft_row.get("likely_service_line") or "").strip() or None

    entry_id = add_entry(
        kind="example",
        content=body,
        service_line=service_line,
        scope="service_line" if service_line else "universal",
        source_queue_id=None,
        confidence=1.0,
        created_by=decided_by,
    )

    db_execute(
        """UPDATE knowledge_library SET
              purpose = 'voice_example',
              user_confirmed_purpose = 'voice_example',
              anika_reasoning = ?
           WHERE id = ?""",
        (f"Auto-saved from approved draft #{draft_row.get('id')} (edited then approved)", entry_id),
    )

    reasoning_log.log(
        agent_name="approver",
        input_obj={
            "decision": "auto_voice_example",
            "draft_id": draft_row.get("id"),
            "service_line": service_line,
        },
        output_obj={"library_id": entry_id},
        draft_id=draft_row.get("id"),
    )
    logger.info("Auto-saved approved draft %s as voice_example (library id=%s)",
                draft_row.get("id"), entry_id)
    return entry_id'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Patched approver.py — auto voice_example save on approve-after-edit")
else:
    print("OLD block not found — approve() signature may differ")

# Verify import
import sys
for mod in list(sys.modules):
    if "approver" in mod or "app.agents" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.agents import approver as _a
    print("approver module imports cleanly")
    print(f"Has _save_as_voice_example: {hasattr(_a, '_save_as_voice_example')}")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
