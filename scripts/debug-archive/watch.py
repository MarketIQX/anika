from app.db import fetch_all
from datetime import datetime, timezone

now = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
print(f"[{now}] Watching Prakash sir's response activity")
print()

rows = fetch_all("""
    SELECT created_at, action, ip_address
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
       AND created_at > datetime('now', '-20 minutes')
     ORDER BY id DESC
""")

if not rows:
    print("  No activity in last 20 min")
else:
    print(f"  {len(rows)} events in last 20 min:")
    for r in rows:
        print(f"    {r['created_at'][11:19]} | {r['action']}")
