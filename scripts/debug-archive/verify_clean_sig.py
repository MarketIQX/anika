from app.db import fetch_one

d = fetch_one("SELECT id, body FROM drafts ORDER BY id DESC LIMIT 1")
print(f"Latest draft: id={d['id']}")
print()
body = d['body']

# Count signatures
print("Signature marker count:")
for marker in ["Warm regards,", "Yours faithfully,", "S V Prakasha", "CA Prakasha", "Wilson Garden"]:
    n = body.count(marker)
    if n > 0:
        print(f"  '{marker}': {n}x")

print()
print("Last 250 chars:")
print(body[-250:])
