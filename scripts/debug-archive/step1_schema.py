from app.db import execute, fetch_all

# Add cognitive_state column to drafts table
cols = fetch_all("PRAGMA table_info(drafts)")
existing = {c["name"] for c in cols}

if "cognitive_state" not in existing:
    execute("ALTER TABLE drafts ADD COLUMN cognitive_state TEXT DEFAULT NULL")
    print("Added drafts.cognitive_state column")
else:
    print("drafts.cognitive_state already exists")

if "voice_coverage_count" not in existing:
    execute("ALTER TABLE drafts ADD COLUMN voice_coverage_count INTEGER DEFAULT 0")
    print("Added drafts.voice_coverage_count column")
else:
    print("drafts.voice_coverage_count already exists")

# Also add is_active to memory if missing — for Fix 2
mem_cols = fetch_all("PRAGMA table_info(memory)")
mem_existing = {c["name"] for c in mem_cols}

if "is_active" not in mem_existing:
    execute("ALTER TABLE memory ADD COLUMN is_active INTEGER DEFAULT 1")
    print("Added memory.is_active column (default 1 for existing rows)")
else:
    print("memory.is_active already exists")

# Verify
print()
print("drafts table schema now:")
for c in fetch_all("PRAGMA table_info(drafts)"):
    if c["name"] in ("id", "sent_status", "cognitive_state", "voice_coverage_count"):
        print(f"  {c['name']:25s} | {c['type']:10s} | default={c['dflt_value']}")

print()
print("memory table schema now:")
for c in fetch_all("PRAGMA table_info(memory)"):
    if c["name"] in ("id", "kind", "is_active"):
        print(f"  {c['name']:25s} | {c['type']:10s} | default={c['dflt_value']}")
