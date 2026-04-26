from app.db import fetch_all
from datetime import datetime, timezone

print(f"Now: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
print()

events = fetch_all("""
    SELECT created_at, user_email, action, target
      FROM access_log
     WHERE julianday('now') - julianday(created_at) < (10.0 / 1440.0)
     ORDER BY id DESC
     LIMIT 30
""")
print(f"Events in last 10 minutes: {len(events)}")
print()
print(f"{'Time':10s} | {'User':12s} | {'Action':15s} | Target")
print("-" * 75)
for e in events:
    user = e['user_email'].split('@')[0]
    target = (e['target'] or '-')[:35]
    print(f"  {e['created_at'][11:19]} | {user:12s} | {e['action']:15s} | {target}")
