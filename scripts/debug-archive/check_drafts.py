from app.db import fetch_all, fetch_one

print("DRAFTS 23 + 24 (today):")
print("=" * 80)

for draft_id in [23, 24]:
    d = fetch_one("""
        SELECT d.id, d.email_id, d.subject, d.body, d.sent_status, d.created_at,
               re.from_email, re.subject AS client_subject
          FROM drafts d
          LEFT JOIN raw_emails re ON d.email_id = re.id
         WHERE d.id = ?
    """, (draft_id,))
    if not d:
        continue
    print()
    print(f"Draft {d['id']} | sent_status={d['sent_status'] or '-'} | {d['created_at'][:19]}")
    print(f"  Client: {d['from_email']}")
    print(f"  Client subject: {d['client_subject']}")
    print(f"  Anika's subject: {d['subject']}")
    print(f"  Anika's body (first 400 chars):")
    print(f"  {'-' * 70}")
    body = d['body'] or ''
    for line in body[:400].split('\n'):
        print(f"    {line}")
    print()
