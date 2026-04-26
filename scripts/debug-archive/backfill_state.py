from app.db import fetch_all, execute
from app.cognitive import library

pending = fetch_all("""
    SELECT d.id, e.likely_service_line
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE d.sent_status = 'pending_approval'
""")

for d in pending:
    sl = d['likely_service_line']
    coverage = library.voice_coverage(sl)
    execute(
        "UPDATE drafts SET cognitive_state = ?, voice_coverage_count = ? WHERE id = ?",
        (coverage['cognitive_state'], coverage['count'], d['id']),
    )
    print(f"Draft {d['id']} ({sl}): state={coverage['cognitive_state']} count={coverage['count']}")
