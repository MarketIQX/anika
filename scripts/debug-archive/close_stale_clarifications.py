from app.db import execute, fetch_all

# Show what will be removed
print("Pending clarifications to remove:")
for r in fetch_all("SELECT id, queue_id, question_text FROM clarifications WHERE status='pending'"):
    print(f"  clar {r['id']} (queue {r['queue_id']}): {r['question_text'][:80]}")

# Soft-close them as rejected (preserves audit trail, won't show in UI)
execute("UPDATE clarifications SET status='answered', answer='reject_stale' WHERE status='pending'")
print()
print("Closed with answer='reject_stale' (audit trail preserved)")

# Verify
remaining = fetch_all("SELECT COUNT(*) n FROM clarifications WHERE status='pending'")
print(f"Remaining pending: {remaining[0]['n']}")
