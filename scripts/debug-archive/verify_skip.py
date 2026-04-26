from app.db import fetch_all

print("=" * 70)
print("META_RULES (should have 0 rules)")
print("=" * 70)
for r in fetch_all("SELECT id, rule_text, target_purpose, created_by FROM meta_rules WHERE is_active=1"):
    print(f"  {r['id']}: {r['target_purpose']} — {r['rule_text'][:60]}")

print()
print("=" * 70)
print("LATEST LIBRARY ENTRIES (should show id=23 with workflow_rule)")
print("=" * 70)
for r in fetch_all("SELECT id, purpose, user_confirmed_purpose, content FROM knowledge_library WHERE is_active=1 ORDER BY id DESC LIMIT 3"):
    print(f"  id={r['id']} purpose={r['purpose']}: {(r['content'] or '')[:60]}")
