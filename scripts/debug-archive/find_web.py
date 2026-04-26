from app.db import fetch_all
rows = fetch_all('''
  SELECT r.id, r.from_email, r.from_name, r.subject, c.category, c.confidence,
         d.id as draft_id, rl.agent_name, rl.status, rl.error_text
  FROM raw_emails r
  LEFT JOIN classifications c ON r.id = c.email_id
  LEFT JOIN drafts d ON r.id = d.email_id
  LEFT JOIN reasoning_log rl ON r.id = rl.email_id
  WHERE r.from_email LIKE '%chandrika%' OR r.subject LIKE '%consult%' OR r.body_plain LIKE '%chandrika%' OR r.subject LIKE '%Want to consult%' OR r.subject LIKE '%Dear Admin%' OR r.body_plain LIKE '%You receive%'
  ORDER BY r.id DESC
''')

if not rows:
    print('Email not found in Anika DB — she never saw it.')
else:
    for r in rows:
        print('id=', r['id'], 'from=', r['from_email'], 'name=', r['from_name'])
        print('  cat=', r['category'], 'conf=', r['confidence'], 'draft=', r['draft_id'])
        print('  subject:', (r['subject'] or '')[:80])
        print('  agent:', r['agent_name'], 'status=', r['status'])
        if r['error_text']:
            print('  ERROR:', r['error_text'])
        print()
