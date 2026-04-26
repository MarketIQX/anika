from app.db import fetch_one

d = fetch_one("""
    SELECT d.id, d.cognitive_state, d.voice_coverage_count,
           e.likely_service_line
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE d.id = 26
""")
print(f"Draft 26:")
print(f"  service_line: {d['likely_service_line']}")
print(f"  cognitive_state: {d['cognitive_state']}")
print(f"  voice_coverage_count: {d['voice_coverage_count']}")

# Check signature integrity too
d2 = fetch_one("SELECT body FROM drafts WHERE id = 26")
body = d2['body']
print()
print("Signature check:")
for marker in ["Warm regards,", "Yours faithfully,", "S V Prakasha", "CA Prakasha", "Wilson Garden"]:
    cnt = body.count(marker)
    if cnt > 0:
        print(f"  '{marker}': {cnt} occurrence(s)")
print()
print("Last 250 chars of body:")
print(body[-250:])
