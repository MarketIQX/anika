from app.db import fetch_all

rows = fetch_all('''
  SELECT r.from_email, r.subject, c.category, c.confidence, c.reasoning as cls_reasoning,
         e.summary as enr_summary, d.id as draft_id,
         rl.agent_name, rl.chain_of_thought, rl.status
  FROM raw_emails r
  LEFT JOIN classifications c ON r.id = c.email_id
  LEFT JOIN enrichments e ON r.id = e.email_id
  LEFT JOIN drafts d ON r.id = d.email_id
  LEFT JOIN reasoning_log rl ON r.id = rl.email_id
  WHERE r.from_email LIKE '%shivank%' OR r.from_email LIKE '%gobel%' OR r.from_email LIKE '%kevin%' OR r.from_email LIKE '%jennifer%'
  ORDER BY r.id, rl.id
''')

for r in rows:
    print(f"FROM: {r['from_email']}")
    print(f"SUBJ: {r['subject']}")
    print(f"CAT:  {r['category']} ({r['confidence']})  -> DRAFT: {r['draft_id']}")
    print(f"AGENT: {r['agent_name']} STATUS: {r['status']}")
    print(f"REASONING: {(r['chain_of_thought'] or '')[:300]}")
    print('---')
