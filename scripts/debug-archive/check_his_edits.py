from app.db import fetch_all
rows = fetch_all('SELECT id, parent_draft_id, subject, LENGTH(body) as len, sent_status FROM drafts WHERE id >= 19 ORDER BY id')
for r in rows:
    print('draft', r['id'], 'parent=', r['parent_draft_id'], 'status=', r['sent_status'], 'len=', r['len'])
    print('  subject:', r['subject'])
