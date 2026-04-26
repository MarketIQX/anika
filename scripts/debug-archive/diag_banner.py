from app.db import fetch_one

# Verify Draft 25 HAS the cognitive_state in DB
d = fetch_one("""
    SELECT d.id, d.cognitive_state, d.voice_coverage_count,
           d.sent_status, e.likely_service_line
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE d.id = 25
""")
print("Draft 25 in DB:")
for k, v in dict(d).items():
    print(f"  {k}: {v}")

# Also fetch via the same query the route uses
print()
print("Same query as the route:")
d2 = fetch_one("""
    SELECT d.*, e.summary, e.likely_service_line, e.urgency, e.routing_partner,
           e.sender_name AS enr_name, e.sender_org, e.sender_country,
           r.from_email, r.from_name, r.subject AS orig_subject,
           r.body_plain AS orig_body, r.received_at
      FROM drafts d
      JOIN raw_emails r ON r.id = d.email_id
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE d.id = 25
""")
for k in ['id', 'cognitive_state', 'voice_coverage_count', 'likely_service_line', 'sent_status']:
    print(f"  {k}: {d2.get(k) if hasattr(d2, 'get') else d2[k] if k in d2.keys() else 'MISSING'}")

# Check template file for the banner syntax
print()
print("Template check — is banner in file?")
from pathlib import Path
t = Path("app/dashboard/templates/draft_detail.html").read_text(encoding="utf-8")
print(f"  'cognitive_state' mentioned: {'cognitive_state' in t}")
print(f"  'cold_start' mentioned:      {'cold_start' in t}")
# Show where it is
import re
m = re.search(r"Cognitive state banner.*?endif.*?%\}", t, re.DOTALL)
if m:
    print(f"  Banner block found, length: {len(m.group())} chars")
    print(f"  First 200 chars: {m.group()[:200]}")
else:
    # Try simpler pattern
    idx = t.find("cognitive_state")
    if idx >= 0:
        print(f"  cognitive_state first appears at char {idx}")
        print(f"  Context: ...{t[max(0,idx-50):idx+250]}...")
