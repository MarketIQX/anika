from app.db import execute, fetch_all
# Restore everything we soft-deleted
execute("UPDATE knowledge_library SET is_active=1, deleted_by=NULL, deleted_at=NULL WHERE id BETWEEN 5 AND 19")
# Restore the queue statuses to approved
execute("UPDATE teaching_queue SET status=? WHERE id IN (7, 9)", ("approved",))
# Keep clarifications answered as-is (Prakash sir chose reject? No — we reset them too)
execute("UPDATE clarifications SET status=?, answer=NULL, answered_at=NULL WHERE id IN (4, 5)", ("pending",))

print("RESTORED. Current active library:")
for r in fetch_all("SELECT id, kind, service_line, scope, content FROM knowledge_library WHERE is_active=1 ORDER BY id"):
    print(f"  id={r['id']} | {r['kind']:8s} | scope={r['scope']:12s} | sl={r['service_line'] or '-'}")
    print(f"    {(r['content'] or '')[:80]}")

print()
print("Pending clarifications:")
for r in fetch_all("SELECT id, queue_id, question_text FROM clarifications WHERE status='pending'"):
    print(f"  clar {r['id']}: {r['question_text']}")
