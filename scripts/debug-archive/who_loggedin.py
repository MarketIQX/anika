from app.db import fetch_all
# Most recent logins from any user
rows = fetch_all("""
    SELECT user_email, created_at, ip_address
      FROM access_log
     WHERE action = 'login_success'
       AND created_at > datetime('now', '-2 hours')
     ORDER BY id DESC
""")
print("Recent logins (last 2h):")
for r in rows:
    print(f"  {r['created_at'][:19]} UTC | {r['user_email']:40s} | {r['ip_address']}")
