from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

# 1. Latest drafts
print("=" * 70)
print("LATEST 5 DRAFTS")
print("=" * 70)
drafts = fetch_all("""
    SELECT d.id, d.sent_status, d.created_at,
           re.from_email, re.subject AS orig_subject
      FROM drafts d
      LEFT JOIN raw_emails re ON re.id = d.email_id
     ORDER BY d.id DESC LIMIT 5
""")
for d in drafts:
    print(f"  draft {d['id']:3d} | {d['sent_status']:20s} | {d['created_at'][:19]} | {d['from_email']}")

# 2. Latest emails received
print()
print("=" * 70)
print("LATEST 5 RAW EMAILS RECEIVED")
print("=" * 70)
emails = fetch_all("""
    SELECT id, from_email, subject, received_at
      FROM raw_emails
     ORDER BY id DESC LIMIT 5
""")
for e in emails:
    print(f"  email {e['id']:3d} | {(e['from_email'] or '?')[:35]:35s} | {(e['received_at'] or '?')[:19]} | {(e['subject'] or '')[:50]}")

# 3. Was Atulya processed?
print()
print("=" * 70)
print("ATULYA — was he processed?")
print("=" * 70)
atulya_email = fetch_one("SELECT id, subject, received_at FROM raw_emails WHERE from_email LIKE '%atulya%' ORDER BY id DESC LIMIT 1")
if atulya_email:
    print(f"  Atulya email id: {atulya_email['id']}, subject: {atulya_email['subject']}")
    draft = fetch_one("SELECT id, sent_status FROM drafts WHERE email_id = ?", (atulya_email['id'],))
    if draft:
        print(f"  -> Draft {draft['id']} created, status: {draft['sent_status']}")
    else:
        print(f"  -> NO draft created yet")
else:
    print("  No Atulya email in raw_emails")

# 4. Recent enricher activity
print()
print("=" * 70)
print("ENRICHER ACTIVITY in last 30 minutes")
print("=" * 70)
recent = fetch_all("""
    SELECT email_id, status, error_text, created_at
      FROM reasoning_log
     WHERE agent_name = 'enricher'
       AND julianday('now') - julianday(created_at) < (30.0 / 1440.0)
     ORDER BY id DESC
""")
if not recent:
    print("  No enricher runs in last 30 min")
else:
    for r in recent:
        err = (r['error_text'] or '-')[:50]
        print(f"  email {r['email_id']:3d} | {r['status']:10s} | {r['created_at'][:19]} | {err}")

# 5. User activity since restart
print()
print("=" * 70)
print("USER ACTIVITY in last 30 min")
print("=" * 70)
acts = fetch_all("""
    SELECT created_at, user_email, action
      FROM access_log
     WHERE julianday('now') - julianday(created_at) < (30.0 / 1440.0)
     ORDER BY id DESC LIMIT 10
""")
for a in acts:
    user_short = a['user_email'].split('@')[0]
    print(f"  {a['created_at'][:19]} | {user_short:12s} | {a['action']}")
