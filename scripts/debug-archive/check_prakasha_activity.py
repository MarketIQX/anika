from app.db import fetch_all, fetch_one

# Last login info
r = fetch_one("""
    SELECT email, last_login_at
      FROM users
     WHERE email = 'prakasha@balakrishnaandco.com'
""")
print("=" * 70)
print("PRAKASH SIR'S USER RECORD")
print("=" * 70)
print(f"Email: {r['email']}")
print(f"Last login: {r['last_login_at']}")

# Recent access log entries
print()
print("=" * 70)
print("RECENT ACTIVITY (last 20 events)")
print("=" * 70)
rows = fetch_all("""
    SELECT action, created_at, ip_address
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC
     LIMIT 20
""")
if not rows:
    print("No activity logged.")
else:
    for r in rows:
        print(f"  {r['created_at'][:19]} | {r['action']:25s} | {r['ip_address'] or '-'}")

# Is he currently online? (login event in last 30 min)
print()
print("=" * 70)
print("SESSION CHECK")
print("=" * 70)
recent = fetch_one("""
    SELECT COUNT(*) n, MAX(created_at) latest
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
       AND created_at > datetime('now', '-30 minutes')
""")
if recent and recent['n'] > 0:
    print(f"Active in last 30 min — {recent['n']} events, last at {recent['latest']}")
else:
    print("No activity in last 30 minutes — not currently active")
