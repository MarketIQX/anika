from app.cognitive import library

print("=" * 80)
print("What Drafter retrieves for NRI tax service")
print("=" * 80)

rules = library.retrieve_rules("nri_tax")
print(f"\nRULES ({len(rules)}):")
for r in rules:
    print(f"  id={r['id']} | {r['kind']:6s} | {(r['content'] or '')[:80]}")

facts = library.retrieve_facts("nri_tax")
print(f"\nFACTS ({len(facts)}):")
for r in facts:
    print(f"  id={r['id']} | {(r['content'] or '')[:80]}")

print()
print("=" * 80)
print("What's EXCLUDED from Drafter (reference_material, document_type, classifier_example)")
print("=" * 80)

from app.db import fetch_all
excluded = fetch_all("""
    SELECT id, purpose, kind, content
      FROM knowledge_library
     WHERE is_active = 1
       AND purpose IN ('reference_material','document_type','classifier_example')
     ORDER BY purpose, id
""")
print(f"\n{len(excluded)} entries excluded:")
for r in excluded:
    print(f"  id={r['id']} | {r['purpose']:20s} | {(r['content'] or '')[:70]}")
