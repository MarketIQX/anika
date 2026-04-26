from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

# Current server time
now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S UTC')
print(f"Server time now: {now_utc}")
print(f"Your IST time:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} + 5:30 hrs")
print()

# Last 10 events (Prakash sir only)
print("=" * 70)
print("PRAKASH SIR — LATEST EVENTS")
print("=" * 70)
rows = fetch_all("""
    SELECT action, created_at, ip_address
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC
     LIMIT 15
""")
for r in rows:
    print(f"  {r['created_at'][:19]} | {r['action']:30s} | {r['ip_address'] or '-'}")

# How long since his last event
latest = fetch_one("""
    SELECT created_at,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) minutes_ago
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC
     LIMIT 1
""")
print()
if latest:
    print(f"Latest event: {latest['created_at'][:19]}")
    print(f"Minutes ago:  {latest['minutes_ago']}")

# All activity in last 6 hours
print()
print("=" * 70)
print("ALL ACTIVITY (any user) IN LAST 6 HOURS")
print("=" * 70)
recent_any = fetch_all("""
    SELECT user_email, action, created_at
      FROM access_log
     WHERE created_at > datetime('now', '-6 hours')
     ORDER BY id DESC
""")
for r in recent_any:
    user_short = r['user_email'].split('@')[0]
    print(f"  {r['created_at'][:19]} | {user_short:12s} | {r['action']}")
