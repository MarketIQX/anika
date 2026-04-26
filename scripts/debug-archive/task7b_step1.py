from app.db import execute, fetch_all

cols = fetch_all("PRAGMA table_info(teaching_queue)")
existing = {c["name"] for c in cols}

additions = [
    ("anika_proposed_purpose",     "TEXT",    "NULL"),
    ("anika_proposed_confidence",  "REAL",    "NULL"),
    ("anika_reasoning",            "TEXT",    "NULL"),
    ("anika_suggested_sl",         "TEXT",    "NULL"),
    ("anika_suggested_custom",     "TEXT",    "NULL"),
    ("humility_articulation",      "TEXT",    "NULL"),
    ("awaiting_confirmation",      "INTEGER", "1"),
]

added = []
for col_name, col_type, default in additions:
    if col_name not in existing:
        execute(f"ALTER TABLE teaching_queue ADD COLUMN {col_name} {col_type} DEFAULT {default}")
        added.append(col_name)

if added:
    print("Added columns:", ", ".join(added))
else:
    print("All columns already exist")

print()
print("teaching_queue schema:")
cols = fetch_all("PRAGMA table_info(teaching_queue)")
for c in cols:
    print(f"  {c['name']:30s} | {c['type']:10s} | default={c['dflt_value']}")
