from app.db import fetch_all

print("=" * 70)
print("KNOWLEDGE LIBRARY — all rows")
print("=" * 70)
rows = fetch_all("SELECT id, is_active, deleted_by, deleted_at FROM knowledge_library ORDER BY id")
print(f"Total rows: {len(rows)}")
active = [r for r in rows if r["is_active"] == 1]
inactive = [r for r in rows if r["is_active"] == 0]
print(f"  Active: {len(active)}")
print(f"  Inactive (soft-deleted): {len(inactive)}")
for r in rows:
    status = "ACTIVE" if r["is_active"] == 1 else f"DELETED by {r['deleted_by']}"
    print(f"  id={r['id']:3d} | {status}")

print()
print("=" * 70)
print("CLARIFICATIONS")
print("=" * 70)
for r in fetch_all("SELECT id, status, answer, answered_at FROM clarifications ORDER BY id"):
    print(f"  clar {r['id']} | status={r['status']} | answer={r['answer']}")

print()
print("=" * 70)
print("TEACHING QUEUE")
print("=" * 70)
for r in fetch_all("SELECT id, status FROM teaching_queue ORDER BY id"):
    print(f"  queue {r['id']} | status={r['status']}")
