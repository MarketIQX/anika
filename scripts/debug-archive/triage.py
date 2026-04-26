from app.db import execute, fetch_all

# Delete ids 5-19 (all the ICICI bank pollution). Keep 1, 2, 4 (AK test entries).
# Soft-delete first to preserve audit
execute("UPDATE knowledge_library SET is_active=0, deleted_by=?, deleted_at=strftime(?, ?) WHERE id BETWEEN 5 AND 19", ("aks@marketiqx.com", "%Y-%m-%dT%H:%M:%fZ", "now"))

# Also close the 2 pending PII clarifications as rejected
execute("UPDATE clarifications SET status=?, answer=?, answered_at=strftime(?, ?) WHERE id IN (4, 5)", ("answered", "reject", "%Y-%m-%dT%H:%M:%fZ", "now"))

# Mark those queue items as rejected
execute("UPDATE teaching_queue SET status=? WHERE id IN (7, 9)", ("rejected",))

# Verify state
print("=" * 70)
print("ACTIVE LIBRARY AFTER TRIAGE")
print("=" * 70)
for r in fetch_all("SELECT id, kind, service_line, scope, content FROM knowledge_library WHERE is_active=1 ORDER BY id"):
    print(f"  id={r['id']} | {r['kind']} | sl={r['service_line'] or '-'} | scope={r['scope']}")
    print(f"    {(r['content'] or '')[:80]}")

print()
print("Soft-deleted (audit preserved):")
for r in fetch_all("SELECT id, content FROM knowledge_library WHERE is_active=0 ORDER BY id"):
    print(f"  id={r['id']}: {(r['content'] or '')[:60]}")

print()
print("Pending clarifications:")
p = fetch_all("SELECT id, status FROM clarifications WHERE status='pending'")
print(f"  {len(p)} pending (should be 0)")
