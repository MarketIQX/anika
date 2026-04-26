import asyncio
from app.db import fetch_one, fetch_all
from app.agents import approver

async def test():
    row = fetch_one("""
        SELECT d.id, d.body, d.parent_draft_id, e.likely_service_line
          FROM drafts d
          LEFT JOIN enrichments e ON e.email_id = d.email_id
         WHERE d.id = 24
    """)
    if not row:
        print("Draft 24 not found")
        return
    draft_row = dict(row)
    print(f"Testing with draft {draft_row['id']}")
    print(f"  parent_draft_id: {draft_row.get('parent_draft_id')}")
    print(f"  service_line: {draft_row.get('likely_service_line')}")
    print(f"  body length: {len(draft_row.get('body') or '')}")
    entry_id = approver._save_as_voice_example(draft_row, decided_by="aks@marketiqx.com")
    print()
    print(f"Created voice_example library entry: id={entry_id}")
    if entry_id:
        entry = fetch_one("SELECT * FROM knowledge_library WHERE id = ?", (entry_id,))
        print()
        print("New library entry:")
        print(f"  purpose: {entry['purpose']}")
        print(f"  service_line: {entry['service_line']}")
        print(f"  kind: {entry['kind']}")
        print(f"  content preview: {(entry['content'] or '')[:200]}")
        print(f"  created_by: {entry['created_by']}")
        print(f"  anika_reasoning: {entry['anika_reasoning']}")

asyncio.run(test())
