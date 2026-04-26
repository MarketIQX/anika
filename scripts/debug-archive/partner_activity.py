from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

for email, label in [
    ("prakasha@balakrishnaandco.com", "Prakash sir"),
    ("prasad@balakrishnaandco.com", "Prasad sir"),
]:
    print(f"=" * 70)
    print(f"{label}")
    print(f"=" * 70)
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

    events = fetch_all("""
        SELECT created_at, action, target
          FROM access_log
         WHERE user_email = ?
         ORDER BY id DESC LIMIT 15
    """, (email,))
    print()
    print(f"  Last 15 events:")
    for e in events:
        target = (e['target'] or '-')[:45]
        print(f"    {e['created_at'][11:19]} UTC | {e['action']:18s} | {target}")
    print()
