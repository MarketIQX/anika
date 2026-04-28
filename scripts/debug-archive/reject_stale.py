from app.db import execute, fetch_one

for draft_id, reason in [
    (43, "Internal partner email — should have been filtered by structural_validator (now fixed in adc3ac4)"),
    (44, "Recruitment inquiry — natural phrasing missed by classifier (now fixed in adc3ac4)"),
]:
    d = fetch_one("SELECT id, sent_status FROM drafts WHERE id = ?", (draft_id,))
    if not d:
        print(f"Draft {draft_id}: not found")
        continue
    if d['sent_status'] != 'pending_approval':
        print(f"Draft {draft_id}: status={d['sent_status']}, not touching")
        continue
    
    execute(
        "UPDATE drafts SET sent_status = 'rejected' WHERE id = ?",
        (draft_id,)
    )
    execute(
        """INSERT INTO approvals (draft_id, decision, decided_by, edit_instruction)
           VALUES (?, 'rejected', ?, ?)""",
        (draft_id, "aks@marketiqx.com", reason)
    )
    print(f"Draft {draft_id}: rejected with audit reason")
