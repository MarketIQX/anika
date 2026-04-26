from pathlib import Path

p = Path("app/cognitive/teaching.py")
code = p.read_text(encoding="utf-8")

# Check if already added
if "def finalize_with_purpose" in code:
    print("Already added — skipping")
else:
    # Find the end of finalize_queue function, insert after it
    new_func = '''

async def finalize_with_purpose(
    queue_id: int,
    *,
    confirmed_purpose: str,
    custom_label: str | None = None,
    service_line: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Finalize a queue row using the user's confirmed purpose.

    Unlike finalize_queue (which runs the Learner to extract multiple units),
    this function is for the Phase 1B flow where Anika proposed a purpose
    and the user confirmed/corrected it. The whole queue content becomes
    ONE library entry with the confirmed purpose.
    """
    row = fetch_one("SELECT * FROM teaching_queue WHERE id=?", (queue_id,))
    if not row:
        raise ValueError(f"teaching_queue {queue_id} not found")

    from app.cognitive.library import add_entry

    # Determine kind based on purpose (purposes map to kinds for legacy compatibility)
    kind_map = {
        "voice_example": "example",
        "classifier_example": "example",
        "document_type": "fact",
        "question_template": "rule",
        "workflow_rule": "rule",
        "firm_fact": "fact",
        "firm_policy": "rule",
        "reference_material": "fact",
    }
    kind = kind_map.get(confirmed_purpose, "fact")

    scope = "service_line" if service_line else "universal"
    is_custom = 1 if custom_label else 0

    # Map from queue content and confirmed purpose → library entry
    entry_id = add_entry(
        kind=kind,
        content=row["raw_content"],
        service_line=service_line,
        scope=scope,
        source_queue_id=queue_id,
        confidence=row.get("anika_proposed_confidence") or 0.9,
        created_by=created_by or row["created_by_user"],
    )

    # Now update the extra classification columns we added in Phase 1B
    execute(
        """UPDATE knowledge_library SET
              purpose = ?,
              anika_proposed_purpose = ?,
              anika_proposed_confidence = ?,
              anika_reasoning = ?,
              user_confirmed_purpose = ?,
              custom_purpose_label = ?,
              is_custom_purpose = ?
           WHERE id = ?""",
        (
            confirmed_purpose,
            row.get("anika_proposed_purpose"),
            row.get("anika_proposed_confidence"),
            row.get("anika_reasoning"),
            confirmed_purpose,
            custom_label,
            is_custom,
            entry_id,
        ),
    )

    # Mark queue as approved
    execute(
        "UPDATE teaching_queue SET status='approved', "
        "processed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
        (queue_id,),
    )

    return {
        "status": "approved",
        "library_id": entry_id,
        "purpose": confirmed_purpose,
    }
'''

    # Append at end of file
    code = code.rstrip() + "\n" + new_func
    p.write_text(code, encoding="utf-8")
    print("Added finalize_with_purpose function")

# Verify import
import sys
for mod in list(sys.modules):
    if "teaching" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.cognitive import teaching
print("teaching module imports clean")
print("Functions:", [f for f in dir(teaching) if not f.startswith("_")])
