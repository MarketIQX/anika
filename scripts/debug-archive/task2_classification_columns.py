from app.db import execute, fetch_all

cols = fetch_all("PRAGMA table_info(knowledge_library)")
existing = {c["name"] for c in cols}

added = []

if "anika_proposed_purpose" not in existing:
    execute("ALTER TABLE knowledge_library ADD COLUMN anika_proposed_purpose TEXT DEFAULT NULL")
    added.append("anika_proposed_purpose")

if "anika_proposed_confidence" not in existing:
    execute("ALTER TABLE knowledge_library ADD COLUMN anika_proposed_confidence REAL DEFAULT NULL")
    added.append("anika_proposed_confidence")

if "anika_reasoning" not in existing:
    execute("ALTER TABLE knowledge_library ADD COLUMN anika_reasoning TEXT DEFAULT NULL")
    added.append("anika_reasoning")

if "user_confirmed_purpose" not in existing:
    execute("ALTER TABLE knowledge_library ADD COLUMN user_confirmed_purpose TEXT DEFAULT NULL")
    added.append("user_confirmed_purpose")

if added:
    print("Added columns:", ", ".join(added))
else:
    print("All columns already exist")

# Verify
cols = fetch_all("PRAGMA table_info(knowledge_library)")
print()
print("Current schema:")
for c in cols:
    default = c["dflt_value"] or "NULL"
    print(f"  {c['name']:30s} | {c['type']:10s} | default={default}")
