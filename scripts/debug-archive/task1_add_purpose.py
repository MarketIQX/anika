from app.db import execute, fetch_all

cols = fetch_all("PRAGMA table_info(knowledge_library)")
has_purpose = any(c["name"] == "purpose" for c in cols)

if not has_purpose:
    # SQLite ALTER TABLE doesn't accept parameterized DEFAULT — inline the string
    execute("ALTER TABLE knowledge_library ADD COLUMN purpose TEXT DEFAULT 'voice_example'")
    print("Added purpose column (default=voice_example)")
else:
    print("Purpose column already exists")

cols = fetch_all("PRAGMA table_info(knowledge_library)")
print()
print("All columns in knowledge_library:")
for c in cols:
    print(f"  {c['name']:20s} | {c['type']:10s} | default={c['dflt_value']}")

print()
rows = fetch_all("SELECT purpose, COUNT(*) n FROM knowledge_library GROUP BY purpose")
print("Entries by purpose:")
for r in rows:
    print(f"  {r['purpose']}: {r['n']}")
