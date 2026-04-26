from pathlib import Path
from app.db import fetch_one, fetch_all

# 1. Look at the latest draft's full body
print("=" * 80)
print("LATEST DRAFT BODY — full")
print("=" * 80)
latest = fetch_one("""
    SELECT id, body, created_at, email_id
      FROM drafts
     ORDER BY id DESC LIMIT 1
""")
print(f"Draft {latest['id']}:")
print(latest['body'])
print()
print("=" * 80)

# 2. Locked signature from firm_identity
print("LOCKED SIGNATURE (firm_identity.py):")
print("-" * 80)
from app.config import firm_identity
print(firm_identity.SIGNATURE_BLOCK)
print("-" * 80)

# 3. Check ensure_signature logic
print()
print("ensure_signature function:")
print("-" * 80)
firm_path = Path("app/config/firm_identity.py")
content = firm_path.read_text(encoding="utf-8")
import re
m = re.search(r"def ensure_signature.*?(?=\ndef |\Z)", content, re.DOTALL)
if m:
    print(m.group())

# 4. Check if any library entry contains "S V Prakasha" pattern (the salesy signature)
print()
print("LIBRARY ENTRIES matching 'S V Prakasha' or 'Wilson Garden':")
print("-" * 80)
rows = fetch_all("""
    SELECT id, purpose, kind, substr(content, 1, 200) preview
      FROM knowledge_library
     WHERE is_active = 1
       AND (content LIKE '%S V Prakasha%'
         OR content LIKE '%Wilson Garden%'
         OR content LIKE '%Partner%')
""")
for r in rows:
    print(f"  id={r['id']} | {r['purpose']:20s} | kind={r['kind']}")
    print(f"    preview: {r['preview']}")
    print()

# 5. Check memory table for same pattern
print()
print("MEMORY table entries matching these patterns:")
print("-" * 80)
rows2 = fetch_all("""
    SELECT id, kind, subject, substr(content, 1, 200) preview
      FROM memory
     WHERE content LIKE '%S V Prakasha%'
        OR content LIKE '%Wilson Garden%'
""")
for r in rows2:
    print(f"  id={r['id']} | kind={r['kind']} | subject={r['subject']}")
    print(f"    preview: {r['preview']}")
    print()

# 6. Check agent_prompts — does any drafter prompt have a signature baked in?
print()
print("DRAFTER PROMPTS — search for signature patterns:")
print("-" * 80)
rows3 = fetch_all("""
    SELECT id, agent, version, is_active, substr(system_prompt, 1, 500) prompt_preview
      FROM agent_prompts
     WHERE agent = 'drafter'
       AND (system_prompt LIKE '%S V Prakasha%' OR system_prompt LIKE '%Wilson Garden%' OR system_prompt LIKE '%Warm regards%')
""")
for r in rows3:
    active = "ACTIVE" if r['is_active'] else ""
    print(f"  {r['agent']} v{r['version']} {active}")
    print(f"    preview: {r['prompt_preview']}")
    print()
