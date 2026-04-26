from app.db import execute, fetch_all

cols = fetch_all("PRAGMA table_info(knowledge_library)")
existing = {c["name"] for c in cols}

added = []

if "custom_purpose_label" not in existing:
    execute("ALTER TABLE knowledge_library ADD COLUMN custom_purpose_label TEXT DEFAULT NULL")
    added.append("custom_purpose_label")

if "is_custom_purpose" not in existing:
    execute("ALTER TABLE knowledge_library ADD COLUMN is_custom_purpose INTEGER DEFAULT 0")
    added.append("is_custom_purpose")

if added:
    print("Added columns:", ", ".join(added))
else:
    print("All columns already exist")

# Create index for purpose graduation query (fast lookup of custom labels by usage)
try:
    execute("CREATE INDEX IF NOT EXISTS idx_kl_custom_purpose ON knowledge_library(custom_purpose_label) WHERE is_custom_purpose=1")
    print("Index idx_kl_custom_purpose created")
except Exception as e:
    print("Index creation:", str(e)[:80])

# Verify
print()
print("Full knowledge_library schema:")
cols = fetch_all("PRAGMA table_info(knowledge_library)")
for c in cols:
    default = c["dflt_value"] or "NULL"
    print(f"  {c['name']:30s} | {c['type']:10s} | default={default}")
