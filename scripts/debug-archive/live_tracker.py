import time
import os
from app.db import fetch_all, fetch_one
from datetime import datetime, timezone

REFRESH_SEC = 5  # how often to refresh

def render():
    os.system("cls")  # clear screen on Windows
    now = datetime.now(timezone.utc)
    print(f"=" * 90)
    print(f"  ANIKA LIVE TRACKER — {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"=" * 90)
    print()

    # Per-partner status
    for email, label in [
        ("prakasha@balakrishnaandco.com", "Prakash sir"),
        ("prasad@balakrishnaandco.com", "Prasad sir"),
        ("aks@marketiqx.com", "AK"),
    ]:
        # Last activity
        latest = fetch_one("""
            SELECT created_at, action, target,
                   CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS mins_ago
              FROM access_log
             WHERE user_email = ?
             ORDER BY id DESC LIMIT 1
        """, (email,))

        if latest:
            mins = latest['mins_ago']
            if mins < 5:
                indicator = "[ACTIVE NOW]"
            elif mins < 30:
                indicator = "[recent]"
            elif mins < 1440:
                indicator = "[idle]"
            else:
                indicator = "[offline]"

            target = (latest['target'] or '-')[:40]
            print(f"  {label:14s} {indicator}")
            print(f"    Last:  {latest['action']:15s}  {target}  ({mins}m ago)")
        else:
            print(f"  {label:14s} [never logged in]")

    # Latest 8 events across all users
    print()
    print(f"  RECENT ACTIVITY (last 10 min)")
    print(f"  " + "-" * 86)
    events = fetch_all("""
        SELECT created_at, user_email, action, target
          FROM access_log
         WHERE julianday('now') - julianday(created_at) < (10.0 / 1440.0)
         ORDER BY id DESC LIMIT 12
    """)
    if not events:
        print(f"    (no activity in last 10 min)")
    else:
        for e in events:
            user = e['user_email'].split('@')[0]
            target = (e['target'] or '-')[:35]
            print(f"    {e['created_at'][11:19]} | {user:10s} | {e['action']:15s} | {target}")

    # Pending drafts
    print()
    print(f"  PENDING DRAFTS")
    print(f"  " + "-" * 86)
    pending = fetch_all("""
        SELECT d.id, d.cognitive_state, e.likely_service_line, re.from_email
          FROM drafts d
          LEFT JOIN enrichments e ON e.email_id = d.email_id
          LEFT JOIN raw_emails re ON re.id = d.email_id
         WHERE d.sent_status = 'pending_approval'
         ORDER BY d.id DESC
    """)
    if not pending:
        print(f"    (no drafts awaiting approval)")
    else:
        for d in pending:
            sl = (d['likely_service_line'] or '-')[:18]
            cog = (d['cognitive_state'] or '-')[:10]
            sender = (d['from_email'] or '-')[:30]
            print(f"    draft {d['id']:3d} | {cog:10s} | {sl:18s} | {sender}")

    print()
    print(f"  Refreshing every {REFRESH_SEC}s. Ctrl+C to stop.")

# Loop
try:
    while True:
        render()
        time.sleep(REFRESH_SEC)
except KeyboardInterrupt:
    print()
    print("Stopped.")
