from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

prasad_latest = fetch_one("""
    SELECT created_at, action,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS minutes_ago
      FROM access_log
     WHERE user_email = 'prasad@balakrishnaandco.com'
     ORDER BY id DESC LIMIT 1
""")

print("=" * 70)
print("PRASAD SIR — login check")
print("=" * 70)
if prasad_latest:
    mins = prasad_latest['minutes_ago']
    print(f"  Last event: {prasad_latest['action']} at {prasad_latest['created_at'][:19]} UTC")
    print(f"  That was {mins} minutes ago")
    print()
    # All his events
    events = fetch_all("""
        SELECT created_at, action
          FROM access_log
         WHERE user_email = 'prasad@balakrishnaandco.com'
         ORDER BY id DESC
    """)
    print(f"Total events: {len(events)}")
    for e in events:
        print(f"  {e['created_at'][:19]} UTC | {e['action']}")
else:
    print("  Prasad sir has NOT logged in yet.")

# User table — last_login timestamp
print()
print("=" * 70)
print("USERS table — last_login_at")
print("=" * 70)
users_rows = fetch_all("SELECT email, last_login_at FROM users ORDER BY id")
for u in users_rows:
    print(f"  {u['email']:40s} | last_login: {u['last_login_at'] or 'never'}")
