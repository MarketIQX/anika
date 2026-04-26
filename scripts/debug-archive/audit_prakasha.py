from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now_utc = datetime.now(timezone.utc)
print(f"Now (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Now (IST): {(now_utc.strftime('%H:%M'))} UTC + 5:30 hrs")
print()

# Latest event overall for Prakash sir
latest = fetch_one("""
    SELECT created_at, action,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS minutes_ago
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC LIMIT 1
""")
if latest:
    print(f"Prakash sir's LATEST event: {latest['action']} at {latest['created_at'][:19]}")
    print(f"That was {latest['minutes_ago']} minutes ago")
print()

# Events in last 60 minutes
print("=" * 70)
print("PRAKASH SIR — events in last 60 minutes")
print("=" * 70)
recent = fetch_all("""
    SELECT created_at, action
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
       AND julianday('now') - julianday(created_at) < (60.0 / 1440.0)
     ORDER BY id DESC
""")
if not recent:
    print("  No activity in last 60 min.")
else:
    for r in recent:
        print(f"  {r['created_at'][11:19]} UTC | {r['action']}")

# Any drafts created or changed today?
print()
print("=" * 70)
print("DRAFT ACTIVITY today (last 24h)")
print("=" * 70)
drafts = fetch_all("""
    SELECT id, sent_status, created_at, parent_draft_id
      FROM drafts
     WHERE julianday('now') - julianday(created_at) < 1
     ORDER BY id DESC
""")
if not drafts:
    print("  No new drafts in 24h.")
else:
    for d in drafts:
        parent = f" (edit of #{d['parent_draft_id']})" if d['parent_draft_id'] else ""
        print(f"  draft {d['id']:3d} | {d['sent_status']:20s} | {d['created_at'][:19]}{parent}")

# Library growth since Prakash sir's last activity
print()
print("=" * 70)
print("LIBRARY GROWTH (entries created since his last event)")
print("=" * 70)
if latest:
    new = fetch_all("""
        SELECT id, purpose, service_line, created_by, substr(content, 1, 60) preview
          FROM knowledge_library
         WHERE is_active = 1
           AND created_at > ?
         ORDER BY id DESC
    """, (latest['created_at'],))
    if not new:
        print("  No new library entries.")
    else:
        for e in new:
            by = (e['created_by'] or '?').split('@')[0]
            print(f"  id={e['id']} | {e['purpose']:20s} | {e['service_line'] or '-':15s} | by {by} | {e['preview']}")
