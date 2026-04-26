from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

now = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
print(f"[{now}] Prakash sir's session monitor")
print()

# Latest events
rows = fetch_all("""
    SELECT created_at, action
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
       AND created_at > datetime('now', '-60 minutes')
     ORDER BY id DESC
     LIMIT 10
""")
print("Last 60 min events:")
if not rows:
    print("  (none)")
for r in rows:
    print(f"  {r['created_at'][11:19]} | {r['action']}")

# Pending proposals awaiting his confirmation
print()
pending = fetch_all("""
    SELECT id, anika_proposed_purpose, anika_proposed_confidence, created_at
      FROM teaching_queue
     WHERE created_by_user = 'prakasha@balakrishnaandco.com'
       AND awaiting_confirmation = 1
     ORDER BY id DESC
""")
print(f"Proposals awaiting HIS confirmation: {len(pending)}")
for p in pending:
    conf = f"{p['anika_proposed_confidence']*100:.0f}%" if p['anika_proposed_confidence'] else "-"
    print(f"  queue {p['id']:3d} | proposed={p['anika_proposed_purpose']:20s} | conf={conf:5s} | at {p['created_at'][11:19]}")

# What he's already confirmed today
print()
confirmed = fetch_all("""
    SELECT kl.id, kl.purpose, kl.service_line,
           substr(kl.content, 1, 60) preview
      FROM knowledge_library kl
     WHERE kl.is_active = 1
       AND kl.created_by = 'prakasha@balakrishnaandco.com'
       AND kl.created_at > datetime('now', '-60 minutes')
     ORDER BY kl.id DESC
""")
print(f"Library entries he's added in last 60 min: {len(confirmed)}")
for c in confirmed:
    sl = c['service_line'] or '-'
    print(f"  id={c['id']:3d} | {c['purpose']:20s} | {sl:15s} | {c['preview']}")
