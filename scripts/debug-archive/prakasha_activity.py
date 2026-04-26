from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

email = "prakasha@balakrishnaandco.com"

latest = fetch_one("""
    SELECT created_at, action, target,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS mins
      FROM access_log
     WHERE user_email = ?
     ORDER BY id DESC LIMIT 1
""", (email,))

print("=" * 70)
print("Prakash sir — latest activity")
print("=" * 70)
if latest:
    mins = latest['mins']
    hrs = mins // 60
    if mins < 5:
        indicator = "ACTIVE NOW"
    elif mins < 30:
        indicator = "recently active"
    elif mins < 120:
        indicator = "idle (last hour)"
    else:
        indicator = "offline"
    print(f"  Status: {indicator}")
    print(f"  Last: {latest['action']} -> {(latest['target'] or '-')[:40]}")
    print(f"  At: {latest['created_at'][:19]} UTC ({hrs}h {mins%60}m ago)")

print()
print("Last 20 events:")
events = fetch_all("""
    SELECT created_at, action, target
      FROM access_log
     WHERE user_email = ?
     ORDER BY id DESC LIMIT 20
""", (email,))
for e in events:
    target = (e['target'] or '-')[:50]
    print(f"  {e['created_at'][:19]} UTC | {e['action']:18s} | {target}")
