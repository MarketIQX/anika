from app.db import fetch_all, fetch_one
from pathlib import Path

print("=" * 80)
print("REAL QUESTION — does Anika learn from edits + remember + use her learning?")
print("=" * 80)

# First — actual reasoning_log schema
print()
print("reasoning_log columns (actual):")
for c in fetch_all("PRAGMA table_info(reasoning_log)"):
    print(f"  {c['name']:25s} | {c['type']}")

# Step 2 — edit classification (try the right column names)
print()
print("STEP 2 — does anything log the edit signal?")
print("-" * 80)
cols = [c['name'] for c in fetch_all("PRAGMA table_info(reasoning_log)")]
# Common column name candidates
agent_col = "agent_name" if "agent_name" in cols else "step" if "step" in cols else None
if agent_col:
    rows = fetch_all(f"""
        SELECT id, {agent_col} AS a, created_at
          FROM reasoning_log
         WHERE created_at > datetime('now', '-24 hours')
         ORDER BY id DESC LIMIT 15
    """)
    if rows:
        print(f"  Last 15 reasoning_log entries (agent_col={agent_col}):")
        for r in rows:
            print(f"    {r['created_at'][11:19]} | {r['a']}")
    else:
        print("  No reasoning_log entries in 24h — learner may not have fired")

# Step 3 — what actually happens when draft is edited?
# Look at routes.py for the draft edit handler
print()
print("STEP 3 — what does the draft_edit route do with the edit?")
print("-" * 80)
code = Path("app/dashboard/routes.py").read_text(encoding="utf-8")
import re
m = re.search(r"async def draft_edit.*?(?=\n@router|\nasync def )", code, re.DOTALL)
if m:
    body = m.group()
    print(f"  Function length: {len(body)} chars")
    # Look for key signals
    calls_learner = "learner" in body.lower()
    creates_lib_entry = "add_entry" in body or "INSERT INTO knowledge_library" in body
    creates_memory = "memory" in body.lower()
    logs_reasoning = "reasoning_log" in body
    print(f"  Calls learner:          {calls_learner}")
    print(f"  Creates library entry:  {creates_lib_entry}")
    print(f"  Stores in memory table: {creates_memory}")
    print(f"  Logs reasoning:         {logs_reasoning}")
    # Print the actual body (trimmed)
    print()
    print("  Function body (first 1500 chars):")
    print(body[:1500])

# Step 4 — voice_example retrieval confirmed working?
print()
print("STEP 4 — voice arsenal right now")
print("-" * 80)
voices = fetch_all("""
    SELECT id, service_line, applied_count, substr(content, 1, 80) preview
      FROM knowledge_library
     WHERE is_active=1 AND purpose='voice_example'
""")
print(f"  {len(voices)} voice_example entries:")
for v in voices:
    sl = v['service_line'] or '-'
    print(f"    id={v['id']} | {sl:20s} | applied_count={v['applied_count']} | {v['preview']}")

# Step 5 — what memory table contains
print()
print("STEP 5 — memory table (legacy voice storage)")
print("-" * 80)
try:
    memrows = fetch_all("""
        SELECT COUNT(*) n FROM memory
    """)
    if memrows:
        print(f"  memory table has {memrows[0]['n']} rows")
        # Show sample
        sample = fetch_all("SELECT * FROM memory LIMIT 3")
        for s in sample:
            print(f"    {dict(s)}")
except Exception as e:
    print(f"  Error: {e}")
