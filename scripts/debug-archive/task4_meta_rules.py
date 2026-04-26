from app.db import execute, fetch_all

# Create meta_rules table
execute("""
    CREATE TABLE IF NOT EXISTS meta_rules (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_text           TEXT NOT NULL,
        trigger_pattern     TEXT,
        target_purpose      TEXT NOT NULL,
        target_service_line TEXT,
        priority            INTEGER DEFAULT 0,
        is_active           INTEGER DEFAULT 1,
        applied_count       INTEGER DEFAULT 0,
        created_by          TEXT NOT NULL,
        deleted_by          TEXT,
        deleted_at          TEXT,
        created_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        updated_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )
""")
print("Created meta_rules table")

# Auto-update updated_at trigger
execute("""
    CREATE TRIGGER IF NOT EXISTS mr_touch_updated_at
    AFTER UPDATE ON meta_rules
    FOR EACH ROW
    BEGIN
        UPDATE meta_rules SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = OLD.id;
    END
""")
print("Created mr_touch_updated_at trigger")

# Index on is_active for fast lookup
execute("CREATE INDEX IF NOT EXISTS idx_meta_rules_active ON meta_rules(is_active, priority DESC)")
print("Created idx_meta_rules_active")

# Verify
print()
print("meta_rules schema:")
cols = fetch_all("PRAGMA table_info(meta_rules)")
for c in cols:
    default = c["dflt_value"] or "NULL"
    print(f"  {c['name']:25s} | {c['type']:10s} | default={default}")

count = fetch_all("SELECT COUNT(*) n FROM meta_rules")
print()
print(f"meta_rules rows: {count[0]['n']}")
