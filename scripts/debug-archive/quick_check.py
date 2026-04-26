from app.db import fetch_one

# Prakash sir's last event vs baseline 08:46:22
latest = fetch_one("""
    SELECT created_at, action
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC LIMIT 1
""")

baseline = "2026-04-24T08:46:22.945Z"
if latest and latest['created_at'] > baseline:
    print(f"CHANGE — new activity: {latest['action']} at {latest['created_at'][:19]}")
else:
    print(f"No change since {baseline[:19]}")

# Also check — was Draft 24 approved?
draft_24 = fetch_one("SELECT id, sent_status FROM drafts WHERE id = 24")
if draft_24:
    print(f"Draft 24 status: {draft_24['sent_status']}")
