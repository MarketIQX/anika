from pathlib import Path
import re

# 1. approver module — see what edit() does
p = Path("app/agents/approver.py")
if p.exists():
    code = p.read_text(encoding="utf-8")
    print("=" * 80)
    print("approver.py — edit function")
    print("=" * 80)
    m = re.search(r"async def edit\(.*?(?=\nasync def |\ndef |\Z)", code, re.DOTALL)
    if m:
        print(m.group()[:3000])

print()
print("=" * 80)
print("learner.py — the agent that classified the edit")
print("=" * 80)
p2 = Path("app/agents/learner.py")
if p2.exists():
    code2 = p2.read_text(encoding="utf-8")
    # Show function signatures
    for m in re.finditer(r"(async )?def (\w+)\(", code2):
        print(f"  {m.group()}")
    # Key part: what does learner return?
    output_type = re.search(r"class\s+(\w+Output\w*)\s*\(BaseModel\)", code2)
    if output_type:
        print(f"\n  Output type: {output_type.group(1)}")

# 3. reasoning_log entry for the 08:24:21 learner fire
from app.db import fetch_one
print()
print("=" * 80)
print("Reasoning_log entry for the learner fire at 08:24:21")
print("=" * 80)
row = fetch_one("""
    SELECT id, agent_name, email_id, draft_id, input_json, output_json, reasoning_text, status
      FROM reasoning_log
     WHERE agent_name = 'learner'
       AND created_at > '2026-04-24T08:20:00'
     ORDER BY id DESC LIMIT 1
""")
if row:
    print(f"  id={row['id']} | draft_id={row['draft_id']} | status={row['status']}")
    print(f"  reasoning_text: {row['reasoning_text'][:400] if row['reasoning_text'] else '-'}")
    print(f"  output_json: {(row['output_json'] or '')[:400]}")
