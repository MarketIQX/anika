from app.db import fetch_all, execute

# Legacy exemplars (memory id=6,7,8,9) still have old marketing content in their bodies.
# Deactivate them — they won't be retrieved by legacy paths anymore.
# firm_snippet entries (id=1,2,3,11 — positioning facts) stay active.
# Other memory types stay active unless flagged later.

print("Before deactivation:")
for r in fetch_all("SELECT id, kind, is_active, subject FROM memory ORDER BY id"):
    status = "ON " if r['is_active'] else "OFF"
    print(f"  {status} id={r['id']} | {r['kind']:15s} | {(r['subject'] or '')[:50]}")

# Deactivate only exemplars (they're the ones causing salesy drafts)
execute("UPDATE memory SET is_active = 0 WHERE kind = 'exemplar'")

print()
print("After deactivation:")
for r in fetch_all("SELECT id, kind, is_active, subject FROM memory ORDER BY id"):
    status = "ON " if r['is_active'] else "OFF"
    print(f"  {status} id={r['id']} | {r['kind']:15s} | {(r['subject'] or '')[:50]}")

print()
print("Now checking: does retrieve_similar_drafts honor is_active?")
from pathlib import Path
import re
# memory_tool.py may have the retrieval function
for fname in ["app/tools/memory_tool.py", "app/cognitive/memory.py"]:
    p = Path(fname)
    if p.exists():
        content = p.read_text(encoding="utf-8")
        print(f"  {fname}: has is_active filter = {'is_active' in content}")
