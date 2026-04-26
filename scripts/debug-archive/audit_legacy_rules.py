from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

# 1. Schema of the rules and firm_knowledge tables
print("=" * 80)
print("RULES TABLE — schema + count")
print("=" * 80)
cols = fetch_all("PRAGMA table_info(rules)")
for c in cols:
    print(f"  {c['name']:25s} | {c['type']:10s}")
print()
count = fetch_one("SELECT COUNT(*) n FROM rules")
print(f"  Total rules: {count['n']}")

print()
print("=" * 80)
print("FIRM_KNOWLEDGE TABLE — schema + count")
print("=" * 80)
cols = fetch_all("PRAGMA table_info(firm_knowledge)")
for c in cols:
    print(f"  {c['name']:25s} | {c['type']:10s}")
count = fetch_one("SELECT COUNT(*) n FROM firm_knowledge")
print(f"  Total firm_knowledge: {count['n']}")

# 2. Who/what added them — created_at + created_by if those columns exist
print()
print("=" * 80)
print("RULES — earliest and latest entries")
print("=" * 80)
rule_cols = [c['name'] for c in fetch_all("PRAGMA table_info(rules)")]
has_created_by = 'created_by' in rule_cols
has_created_at = 'created_at' in rule_cols

if has_created_at:
    earliest = fetch_one("SELECT * FROM rules ORDER BY created_at ASC LIMIT 1")
    latest = fetch_one("SELECT * FROM rules ORDER BY created_at DESC LIMIT 1")
    print(f"  Earliest: {earliest.get('created_at') if hasattr(earliest, 'get') else 'check'}")
    if earliest:
        for k in earliest.keys():
            print(f"    {k}: {(str(earliest[k]) or '')[:80]}")
    print()
    print(f"  Latest:")
    if latest:
        for k in latest.keys():
            print(f"    {k}: {(str(latest[k]) or '')[:80]}")

# 3. Who added firm_knowledge entries
print()
print("=" * 80)
print("FIRM_KNOWLEDGE — sample entries with timestamps")
print("=" * 80)
fk_cols = [c['name'] for c in fetch_all("PRAGMA table_info(firm_knowledge)")]
print(f"Columns: {fk_cols}")
sample = fetch_all("SELECT * FROM firm_knowledge LIMIT 3")
for r in sample:
    print()
    for k in r.keys():
        v = str(r[k]) if r[k] is not None else 'NULL'
        print(f"    {k}: {v[:100]}")

# 4. backfill_memory.py — does it seed these on startup?
from pathlib import Path
print()
print("=" * 80)
print("backfill_memory.py — what does it seed?")
print("=" * 80)
bf = Path("app/jobs/backfill_memory.py")
if bf.exists():
    code = bf.read_text(encoding="utf-8")
    print(f"File size: {len(code)} chars")
    # Look for INSERT statements
    import re
    for m in re.finditer(r"INSERT INTO (rules|firm_knowledge|memory|agent_prompts)", code, re.IGNORECASE):
        idx = m.start()
        # Show 200 chars context
        print(f"\n  Found '{m.group()}' at position {idx}:")
        print(f"  {code[max(0,idx-100):idx+300]}")
