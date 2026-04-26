from app.db import fetch_all
print("COLUMNS:")
for r in fetch_all("PRAGMA table_info(meta_rules)"):
    print(f"  {r['name']:25s} {r['type']:15s} notnull={r['notnull']} default={r['dflt_value']}")
print()
print("INDEXES:")
for r in fetch_all("PRAGMA index_list(meta_rules)"):
    print(f"  {r['name']} unique={r['unique']}")
print()
print("CREATE SQL:")
for r in fetch_all("SELECT sql FROM sqlite_master WHERE type='table' AND name='meta_rules'"):
    print(r['sql'])
