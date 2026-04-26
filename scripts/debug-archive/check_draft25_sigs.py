from app.db import fetch_one
d = fetch_one("SELECT id, body, sent_status, created_at FROM drafts WHERE id = 25")
print(f"Draft 25 status: {d['sent_status']}")
print(f"Created: {d['created_at']}")
print()
print("FULL BODY:")
print("=" * 70)
print(d['body'])
print("=" * 70)
print()
# Count signatures
body = d['body'] or ''
sigs = ["Warm regards,", "Yours faithfully,", "Best regards,", "Sincerely,"]
for s in sigs:
    count = body.count(s)
    if count > 0:
        print(f"  '{s}' appears {count} time(s)")
