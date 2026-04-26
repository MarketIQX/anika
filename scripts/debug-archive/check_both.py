from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

# Latest event from Prakash sir
latest = fetch_one("""
    SELECT created_at, action,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS minutes_ago
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC LIMIT 1
""")

print("=" * 70)
print("PRAKASH SIR — latest activity")
print("=" * 70)
if latest:
    mins = latest['minutes_ago']
    hrs, m = mins // 60, mins % 60
    print(f"  Last event: {latest['action']} at {latest['created_at'][:19]} UTC")
    print(f"  That was {hrs}h {m}m ago")
print()

# Activity in last 60 min
recent = fetch_all("""
    SELECT created_at, action
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
       AND julianday('now') - julianday(created_at) < (60.0 / 1440.0)
     ORDER BY id DESC
""")
print(f"Events in last 60 min: {len(recent)}")
for r in recent:
    print(f"  {r['created_at'][11:19]} UTC | {r['action']}")

# Prasad sir for comparison
print()
print("=" * 70)
print("PRASAD SIR — has he logged in yet?")
print("=" * 70)
prasad_latest = fetch_one("""
    SELECT created_at, action FROM access_log
     WHERE user_email = 'prasad@balakrishnaandco.com'
     ORDER BY id DESC LIMIT 1
""")
if prasad_latest:
    print(f"  Last event: {prasad_latest['action']} at {prasad_latest['created_at'][:19]} UTC")
else:
    print("  No activity yet")
