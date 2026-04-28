from app.db import fetch_all, fetch_one

print("=" * 70)
print("DRAFT 43 — CS Prashant (internal email, should have been filtered)")
print("=" * 70)
e43 = fetch_one("""
    SELECT re.id, re.from_email, re.from_name, re.to_email, re.subject, 
           re.is_web_form, re.is_reply_in_thread,
           c.category, c.confidence, c.reasoning, c.model
      FROM raw_emails re
      LEFT JOIN classifications c ON c.email_id = re.id
      JOIN drafts d ON d.email_id = re.id
     WHERE d.id = 43
""")
if e43:
    print(f"  from: {e43['from_email']}")
    print(f"  to:   {e43['to_email']}")
    print(f"  is_web_form: {e43['is_web_form']}")
    print(f"  is_reply: {e43['is_reply_in_thread']}")
    print(f"  classifier: {e43['category']} ({e43['model']})")
    print(f"  reasoning:  {(e43['reasoning'] or '')[:300]}")

print()
print("=" * 70)
print("DRAFT 44 — Preethinjeevan (job inquiry, should have been classified as recruitment)")
print("=" * 70)
e44 = fetch_one("""
    SELECT re.id, re.from_email, re.subject, re.body_plain,
           re.is_web_form,
           c.category, c.confidence, c.reasoning, c.model
      FROM raw_emails re
      LEFT JOIN classifications c ON c.email_id = re.id
      JOIN drafts d ON d.email_id = re.id
     WHERE d.id = 44
""")
if e44:
    print(f"  from: {e44['from_email']}")
    print(f"  is_web_form: {e44['is_web_form']}")
    print(f"  classifier: {e44['category']} ({e44['model']})")
    print(f"  reasoning:  {(e44['reasoning'] or '')[:300]}")
    print()
    print(f"  body (first 800 chars):")
    print((e44['body_plain'] or '')[:800])

print()
print("=" * 70)
print("Recent classifier activity — what's been processed today")
print("=" * 70)
recent = fetch_all("""
    SELECT c.email_id, re.from_email, c.category, c.model, c.created_at
      FROM classifications c
      JOIN raw_emails re ON re.id = c.email_id
     WHERE julianday('now') - julianday(c.created_at) < 1
     ORDER BY c.id DESC LIMIT 10
""")
for r in recent:
    print(f"  {r['created_at'][:19]} | {r['category']:25s} | {r['model']:15s} | {r['from_email']}")
