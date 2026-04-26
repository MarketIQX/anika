from app.db import fetch_all

events = fetch_all("""
    SELECT created_at, action, target
      FROM access_log
     WHERE user_email = 'prasad@balakrishnaandco.com'
     ORDER BY id DESC
""")
print(f"Total events: {len(events)}")
for e in events:
    target = e['target'] or '-' if 'target' in e.keys() else '-'
    print(f"  {e['created_at'][:19]} UTC | {e['action']:25s} | {target}")
