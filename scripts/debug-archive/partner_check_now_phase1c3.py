from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

for email, label in [
    ("prakasha@balakrishnaandco.com", "Prakash sir"),
    ("prasad@balakrishnaandco.com", "Prasad sir"),
]:
    print("=" * 70)
    print(label)
    print("=" * 70)
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
            indicator = "ACTIVE NOW"
        elif mins < 120:
            indicator = "active recently"
        elif mins < 720:
            indicator = "active earlier today"
        else:
            indicator = "offline"
        print(f"  Status: {indicator}")
        print(f"  Last:   {latest['action']} -> {(latest['target'] or '-')[:50]}")
        print(f"  At:     {latest['created_at'][:19]} UTC ({hrs}h {mins%60}m ago)")
    else:
        print("  Never logged in")

    events = fetch_all("""
        SELECT created_at, action, target
          FROM access_log
         WHERE user_email = ?
         ORDER BY id DESC LIMIT 12
    """, (email,))
    print()
    print(f"  Last 12 events:")
    for e in events:
        target = (e['target'] or '-')[:50]
        print(f"    {e['created_at'][11:19]} UTC | {e['action']:20s} | {target}")
    print()

# Drafts pending right now
print("=" * 70)
print("Drafts pending approval right now")
print("=" * 70)
pending = fetch_all("""
    SELECT d.id, d.cognitive_state, e.likely_service_line, re.from_email, d.created_at
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
      LEFT JOIN raw_emails re ON re.id = d.email_id
     WHERE d.sent_status = 'pending_approval'
     ORDER BY d.id DESC
""")
print(f"  {len(pending)} pending")
for d in pending:
    print(f"    draft {d['id']:3d} | {(d['cognitive_state'] or '-'):12s} | {(d['likely_service_line'] or '-'):20s} | {d['from_email']}")

# Sent today
print()
print("Sent today:")
sent_today = fetch_all("""
    SELECT id, draft_id, to_email, sent_at, test_mode
      FROM sent_log
     WHERE julianday('now') - julianday(sent_at) < 1
       AND test_mode = 0
     ORDER BY id DESC
""")
print(f"  {len(sent_today)} real sends in last 24h")
for s in sent_today:
    print(f"    sent_log {s['id']} | draft {s['draft_id']} | {s['to_email']} | {s['sent_at'][:19]}")
