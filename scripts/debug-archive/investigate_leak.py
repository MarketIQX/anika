from pathlib import Path
import re

code = Path("app/dashboard/routes.py").read_text(encoding="utf-8")

print("=" * 80)
print("INVESTIGATION — user-scoping audit on /train data")
print("=" * 80)

# 1. Check the /train route's data fetches
print()
print("1. CURRENT /train route queries:")
print("-" * 80)

import re
# Find the train_index function
m = re.search(r"async def train_index.*?(?=\n@router)", code, re.DOTALL)
if m:
    body = m.group()
    # Find all SQL queries within
    queries = re.findall(r'fetch_all\("""(.+?)"""\)|fetch_one\("""(.+?)"""\)|fetch_all\("(.+?)"\)|fetch_one\("(.+?)"\)', body, re.DOTALL)
    print(f"Found {len(queries)} queries in train_index function:")
    for i, q_tuple in enumerate(queries, 1):
        q = next((x for x in q_tuple if x), "")
        has_user_filter = "created_by" in q or "user_email" in q or "created_by_user" in q
        marker = "OK" if has_user_filter else "LEAKS"
        print(f"  Query {i}: [{marker}]")
        for line in q.split("\n")[:6]:
            if line.strip():
                print(f"    {line.strip()[:90]}")
        print()

# 2. Check /train/teach/confirm
print()
print("2. /train/teach/confirm access check:")
print("-" * 80)
m = re.search(r"async def train_teach_confirm.*?(?=\n@router|\nasync def )", code, re.DOTALL)
if m:
    body = m.group()
    # Look for queue_id access without user check
    if "fetch_one" in body and "created_by_user" not in body:
        print("LEAKS: Any user can confirm any queue_id — no ownership check")
    else:
        print("OK: Ownership validated")

# 3. Check /drafts
print()
print("3. /drafts data fetches:")
print("-" * 80)
m = re.search(r"async def drafts_index.*?(?=\n@router|\nasync def )", code, re.DOTALL)
if m:
    body = m.group()
    queries = re.findall(r'fetch_all\("""(.+?)"""\)', body, re.DOTALL)
    for i, q in enumerate(queries, 1):
        if "created_by" in q or "user_email" in q:
            print(f"  Query {i}: [OK]")
        else:
            print(f"  Query {i}: [LEAKS]")

# 4. Check rules, teaching-dashboard, knowledge-graph, inbox
print()
print("4. Other routes:")
print("-" * 80)
routes_to_check = [
    ("train_rules_list", "/train/rules"),
    ("teaching_dashboard", "/teaching-dashboard"),
    ("knowledge_graph", "/knowledge-graph"),
    ("inbox_index", "/inbox"),
]
for fn_name, path in routes_to_check:
    m = re.search(rf"async def {fn_name}.*?(?=\n@router|\nasync def )", code, re.DOTALL)
    if m:
        body = m.group()
        scoped = "created_by" in body or "user_email" in body or "created_by_user" in body
        marker = "OK" if scoped else "LEAKS"
        print(f"  {path:30s} ({fn_name}) : {marker}")
    else:
        print(f"  {path:30s} ({fn_name}) : NOT FOUND")

# 5. Verify the claim — what does teaching_queue actually store for user?
print()
print("5. teaching_queue user tracking:")
print("-" * 80)
from app.db import fetch_all
# Check schema
cols = fetch_all("PRAGMA table_info(teaching_queue)")
user_cols = [c for c in cols if "user" in c["name"].lower() or "by" in c["name"].lower()]
for c in user_cols:
    print(f"  Column: {c['name']} ({c['type']}) default={c['dflt_value']}")

# Check actual data — which user created what
print()
print("  Actual queue rows:")
rows = fetch_all("""
    SELECT id, created_by_user, status, awaiting_confirmation, anika_proposed_purpose
      FROM teaching_queue ORDER BY id DESC LIMIT 15
""")
for r in rows:
    print(f"    queue {r['id']:3d} | user={r['created_by_user']:40s} | status={r['status']:10s} | awaiting={r['awaiting_confirmation']} | {r['anika_proposed_purpose'] or ''}")

# 6. knowledge_library user tracking
print()
print("6. knowledge_library.created_by actual values:")
print("-" * 80)
from app.db import fetch_all
by_user = fetch_all("""
    SELECT created_by, COUNT(*) n FROM knowledge_library
     WHERE is_active=1 GROUP BY created_by
""")
for r in by_user:
    print(f"  {r['created_by'] or 'NULL':40s} | {r['n']} entries")
