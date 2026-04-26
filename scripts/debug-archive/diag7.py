from app.db import fetch_all
rows = fetch_all('''
  SELECT r.id, r.from_email, r.subject, c.category, d.id as draft_id,
         rl.agent_name, rl.status, rl.error_text, rl.prompt_version
  FROM raw_emails r
  LEFT JOIN classifications c ON r.id = c.email_id
  LEFT JOIN drafts d ON r.id = d.email_id
  LEFT JOIN reasoning_log rl ON r.id = rl.email_id AND rl.agent_name='enricher'
  ORDER BY r.id DESC
  LIMIT 15
''')
for r in rows:
    print(f"id={r['id']} cat={r['category']} draft={r['draft_id']} enricher_status={r['status']} v={r['prompt_version']}")
    print(f"  {r['subject'][:70]}")
    if r['error_text']: print(f"  ERROR: {r['error_text']}")
