from app.db import execute, fetch_one
# Soft-delete library id=24 — content is "find attached reply", not a real voice example
execute("""
    UPDATE knowledge_library
       SET is_active = 0,
           deleted_by = 'aks@marketiqx.com',
           deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
     WHERE id = 24
""")
r = fetch_one("SELECT id, is_active, deleted_by FROM knowledge_library WHERE id = 24")
print(f"Library id=24: is_active={r['is_active']}, deleted_by={r['deleted_by']}")

# Also verify what voice_examples are active now
from app.db import fetch_all
voices = fetch_all("""
    SELECT id, service_line, substr(content, 1, 70) preview
      FROM knowledge_library
     WHERE is_active = 1 AND purpose = 'voice_example'
""")
print()
print(f"Active voice_examples: {len(voices)}")
for v in voices:
    print(f"  id={v['id']} | {v['service_line'] or '-':15s} | {v['preview']}")
