from app.db import fetch_all, fetch_one

# All approval rows regardless of decision value
print("All approval decisions in approvals table:")
rows = fetch_all("SELECT decision, COUNT(*) AS n FROM approvals GROUP BY decision ORDER BY n DESC")
for r in rows:
    print(f"  {r['decision']!r}: {r['n']}")

print()
# Specific decision values
print("Sample approval rows for Chandrika's draft 22:")
rows = fetch_all("SELECT id, draft_id, decision, decided_by, created_at FROM approvals WHERE draft_id = 22")
for r in rows:
    print(f"  id={r['id']} draft_id={r['draft_id']} decision={r['decision']!r} by {r['decided_by']} at {r['created_at']}")

# Any test_mode rows in sent_log
print()
print("sent_log breakdown by test_mode:")
rows = fetch_all("SELECT test_mode, COUNT(*) AS n FROM sent_log GROUP BY test_mode")
for r in rows:
    print(f"  test_mode={r['test_mode']}: {r['n']}")
