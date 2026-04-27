from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC ({(now.hour + 5) % 24}:{now.minute:02d} IST approx)")
print()

# Partner activity
for email, label in [
    ("prakasha@balakrishnaandco.com", "Prakash sir"),
    ("prasad@balakrishnaandco.com", "Prasad sir"),
]:
    latest = fetch_one("""
        SELECT created_at, action, target,
               CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS mins
          FROM access_log
         WHERE user_email = ?
         ORDER BY id DESC LIMIT 1
    """, (email,))
    if latest:
        mins = latest['mins']
        hrs = mins // 60
        if mins < 30:
            indicator = "ACTIVE TODAY"
        elif mins < 720:
            indicator = "active this morning/last night"
        else:
            indicator = "offline"
        print(f"  {label}: {indicator} — last: {latest['action']} at {latest['created_at'][:19]} ({hrs}h ago)")
    else:
        print(f"  {label}: never")

# Last 24h emails received
print()
recent = fetch_all("""
    SELECT id, from_email, subject, received_at
      FROM raw_emails
     WHERE julianday('now') - julianday(received_at) < 1
     ORDER BY id DESC
""")
print(f"Emails received in last 24h: {len(recent)}")
for r in recent[:10]:
    print(f"  {r['received_at'][:19]} | {r['from_email']:40s} | {(r['subject'] or '')[:50]}")

# Pending drafts
print()
pending = fetch_all("""
    SELECT d.id, d.cognitive_state, e.likely_service_line, re.from_email
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
      LEFT JOIN raw_emails re ON re.id = d.email_id
     WHERE d.sent_status = 'pending_approval'
     ORDER BY d.id DESC
""")
print(f"Drafts pending approval: {len(pending)}")
for d in pending:
    print(f"  draft {d['id']} | {(d['cognitive_state'] or '-'):12s} | {(d['likely_service_line'] or '-'):20s} | {d['from_email']}")

# Test sanity
print()
print("(Run this separately if you want full pytest):")
print("  .\\.venv\\Scripts\\python.exe -m pytest --tb=no -q")
