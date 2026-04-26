from app.db import fetch_all

print("=" * 80)
print("KNOWLEDGE LIBRARY — WHAT PRAKASH SIR TAUGHT ANIKA")
print("=" * 80)
rows = fetch_all("SELECT id, kind, service_line, scope, applied_count, created_by, created_at, content FROM knowledge_library WHERE is_active=1 ORDER BY id DESC")
print(f"Total active entries: {len(rows)}")
print()
for r in rows:
    print(f"  id={r['id']} | kind={r['kind']:8s} | sl={str(r['service_line'] or '-'):20s} | by={r['created_by']} | applied={r['applied_count']}")
    print(f"    {(r['content'] or '')[:100]}")
    print()

print("=" * 80)
print("TEACHING QUEUE ACTIVITY")
print("=" * 80)
for r in fetch_all("SELECT id, source_type, status, created_by_user, created_at, original_filename FROM teaching_queue ORDER BY id DESC"):
    filename = r['original_filename'] or '-'
    print(f"  queue {r['id']} | {r['source_type']:5s} | {r['status']:25s} | {r['created_by_user']} | {r['created_at'][:19]} | {filename}")

print()
print("=" * 80)
print("PENDING CLARIFICATIONS")
print("=" * 80)
pending = fetch_all("SELECT id, queue_id, question_text FROM clarifications WHERE status='pending'")
if pending:
    for r in pending:
        print(f"  clar {r['id']} (queue {r['queue_id']}): {r['question_text']}")
else:
    print("  None pending — Prakash sir answered everything")

print()
print("=" * 80)
print("KINDS & SERVICE LINE DISTRIBUTION")
print("=" * 80)
for r in fetch_all("SELECT kind, service_line, COUNT(*) n FROM knowledge_library WHERE is_active=1 GROUP BY kind, service_line ORDER BY n DESC"):
    sl = r['service_line'] or 'universal'
    print(f"  {r['kind']:8s} / {sl:25s} : {r['n']}")

print()
print("=" * 80)
print("RECENT ACCESS LOG — Prakash sir's activity")
print("=" * 80)
for r in fetch_all("SELECT action, user_email, created_at FROM access_log WHERE user_email = 'prakasha@balakrishnaandco.com' ORDER BY id DESC LIMIT 20"):
    print(f"  {r['created_at'][:19]} | {r['action']}")
