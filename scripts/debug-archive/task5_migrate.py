from app.db import execute, fetch_all

migration = {
    1:  ("firm_policy",         True),
    2:  ("firm_fact",           True),
    4:  ("firm_fact",           True),
    5:  ("classifier_example",  True),
    6:  ("reference_material",  True),
    7:  ("reference_material",  True),
    8:  ("reference_material",  True),
    9:  ("reference_material",  True),
    10: ("reference_material",  True),
    11: ("document_type",       True),
    12: ("document_type",       True),
    13: ("classifier_example",  True),
    14: ("reference_material",  True),
    15: ("reference_material",  True),
    16: ("reference_material",  True),
    17: ("reference_material",  True),
    18: ("reference_material",  True),
    19: ("document_type",       True),
}

updated = 0
for entry_id, (new_purpose, confirmed) in migration.items():
    confirmed_value = new_purpose if confirmed else None
    execute(
        "UPDATE knowledge_library SET purpose = ?, user_confirmed_purpose = ? WHERE id = ?",
        (new_purpose, confirmed_value, entry_id),
    )
    updated += 1

print(f"Migrated {updated} entries.")
print()

print("=" * 95)
print("LIBRARY AFTER MIGRATION")
print("=" * 95)
rows = fetch_all("""
    SELECT id, purpose, user_confirmed_purpose, kind, service_line, content
      FROM knowledge_library
     WHERE is_active = 1
     ORDER BY purpose, id
""")
current = None
for r in rows:
    if r["purpose"] != current:
        current = r["purpose"]
        print()
        print(f"--- {current} ---")
    print(f"  id={r['id']:3d} | kind={r['kind']:8s} | sl={r['service_line'] or '-':15s}")
    print(f"       {(r['content'] or '')[:100]}")

print()
print("=" * 95)
print("PURPOSE DISTRIBUTION")
print("=" * 95)
dist = fetch_all("""
    SELECT purpose, COUNT(*) total
      FROM knowledge_library
     WHERE is_active = 1
  GROUP BY purpose
  ORDER BY total DESC
""")
for d in dist:
    print(f"  {d['purpose']:25s} : {d['total']:3d}")
