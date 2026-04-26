from app.db import execute, fetch_one

execute("""
    UPDATE drafts
       SET sent_status = 'rejected',
           updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
     WHERE id = 27 AND sent_status = 'pending_approval'
""")

execute("""
    INSERT INTO approvals (draft_id, decision, edit_instruction, decided_by, created_at)
    VALUES (27, 'rejected', 'auto-rejected: recruitment enquiry, should not have been drafted', 'aks@marketiqx.com', strftime('%Y-%m-%dT%H:%M:%fZ','now'))
""")

d = fetch_one("SELECT id, sent_status FROM drafts WHERE id = 27")
print(f"Draft 27: status = {d['sent_status']}")

# Show clean state of pending drafts
print()
pending = fetch_one("SELECT COUNT(*) n FROM drafts WHERE sent_status = 'pending_approval'")
print(f"Pending approval queue: {pending['n']} drafts")
