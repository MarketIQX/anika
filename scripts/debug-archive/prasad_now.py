from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

# Latest activity from Prasad sir
print("=" * 70)
print("PRASAD SIR — recent events from access_log")
print("=" * 70)
events = fetch_all("""
    SELECT created_at, action, target,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS minutes_ago
      FROM access_log
     WHERE user_email = 'prasad@balakrishnaandco.com'
     ORDER BY id DESC
""")
print(f"Total events: {len(events)}")
for e in events:
    print(f"  {e['created_at'][:19]} | {e['action']:30s} | target={e['target'] or '-'} | {e['minutes_ago']} min ago")

# Anything he created/edited?
print()
print("=" * 70)
print("LIBRARY — anything new since his login?")
print("=" * 70)
new_lib = fetch_all("""
    SELECT id, purpose, service_line, created_by, substr(content, 1, 70) preview, created_at
      FROM knowledge_library
     WHERE is_active = 1
       AND created_at > '2026-04-25T05:25:27'
     ORDER BY id DESC
""")
if not new_lib:
    print("  No new library entries since Prasad sir's login")
else:
    for r in new_lib:
        by = (r['created_by'] or '?').split('@')[0]
        print(f"  id={r['id']:3d} | {r['purpose']:20s} | by {by:10s} | {r['preview']}")

# Drafts touched (any status changes since login?)
print()
print("=" * 70)
print("DRAFTS — any state changes since his login?")
print("=" * 70)
drafts = fetch_all("""
    SELECT id, sent_status, updated_at
      FROM drafts
     WHERE updated_at > '2026-04-25T05:25:27'
     ORDER BY id DESC
""")
if not drafts:
    print("  No draft state changes since his login (no approves/edits/rejects)")
else:
    for d in drafts:
        print(f"  draft {d['id']} | {d['sent_status']:20s} | updated {d['updated_at'][:19]}")

# Any new approvals?
print()
print("=" * 70)
print("APPROVALS — any actions on drafts?")
print("=" * 70)
approvals = fetch_all("""
    SELECT id, draft_id, decision, decided_by, created_at
      FROM approvals
     WHERE created_at > '2026-04-25T05:25:27'
     ORDER BY id DESC
""")
if not approvals:
    print("  No draft approvals/edits/rejects since his login")
else:
    for a in approvals:
        by = (a['decided_by'] or '?').split('@')[0]
        print(f"  approval {a['id']} | draft={a['draft_id']} | {a['decision']:10s} | by {by} | {a['created_at'][:19]}")

# Server log — what's he viewed via GET?
# Get his IP first
print()
print("=" * 70)
print("RECENT GMAIL POLL ACTIVITY")
print("=" * 70)
recent_emails = fetch_all("""
    SELECT id, from_email, subject, received_at
      FROM raw_emails
     WHERE received_at > '2026-04-25T04:00:00'
     ORDER BY id DESC LIMIT 5
""")
for r in recent_emails:
    print(f"  email {r['id']:3d} | {r['from_email']:35s} | {r['received_at'][:19]} | {(r['subject'] or '')[:50]}")
