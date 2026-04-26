from app.db import fetch_all

print("=" * 90)
print("LATEST LIBRARY ENTRIES (to see if the new one was created)")
print("=" * 90)
rows = fetch_all("""
    SELECT id, purpose, user_confirmed_purpose, anika_proposed_purpose,
           anika_proposed_confidence, service_line, created_by, content
      FROM knowledge_library
     WHERE is_active = 1
     ORDER BY id DESC
     LIMIT 5
""")
for r in rows:
    print()
    print(f"id={r['id']} | purpose={r['purpose']}")
    print(f"  anika proposed: {r['anika_proposed_purpose']} (conf {r['anika_proposed_confidence']})")
    print(f"  user confirmed: {r['user_confirmed_purpose']}")
    print(f"  service_line: {r['service_line']}")
    print(f"  by: {r['created_by']}")
    print(f"  content: {(r['content'] or '')[:80]}")

print()
print("=" * 90)
print("TEACHING QUEUE STATUS")
print("=" * 90)
for r in fetch_all("""
    SELECT id, status, awaiting_confirmation, anika_proposed_purpose,
           created_at
      FROM teaching_queue
     ORDER BY id DESC LIMIT 5
"""):
    print(f"queue {r['id']} | status={r['status']} | awaiting={r['awaiting_confirmation']} | proposed={r['anika_proposed_purpose']}")

print()
print("=" * 90)
print("META-RULES (should be empty unless you corrected Anika)")
print("=" * 90)
for r in fetch_all("SELECT id, rule_text, target_purpose, created_by FROM meta_rules WHERE is_active=1"):
    print(f"rule {r['id']} | target={r['target_purpose']} | by={r['created_by']}")
    print(f"  {r['rule_text'][:100]}")
