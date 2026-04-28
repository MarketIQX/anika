"""Compare Anika's draft body vs Prakash sir's actual sent reply
for the threads where the harvester caught a bypass."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.db import fetch_all, fetch_one

# Find drafts that got bypassed AND we have the harvested reply for
bypassed_drafts = fetch_all("""
    SELECT d.id AS draft_id, d.body AS anika_body, d.created_at AS draft_at,
           re.from_email, re.subject,
           e.likely_service_line
      FROM drafts d
      JOIN raw_emails re ON re.id = d.email_id
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE d.sent_status = 'rejected_partner_replied_outside'
     ORDER BY d.id DESC
""")

for d in bypassed_drafts:
    print("=" * 70)
    print(f"DRAFT {d['draft_id']} — {d['from_email']}")
    print(f"Service line: {d['likely_service_line'] or '-'}")
    print(f"Subject: {d['subject']}")
    print("=" * 70)
    print()
    print("--- ANIKA'S DRAFT (what she suggested) ---")
    anika_body = (d['anika_body'] or '').strip()
    print(anika_body[:1500])
    if len(anika_body) > 1500:
        print(f"... [truncated, total {len(anika_body)} chars]")
    print()
    
    # Find the harvested reply for this thread
    # Match by service_line + harvest_source + recent
    harvested = fetch_one("""
        SELECT id, content, created_at
          FROM knowledge_library
         WHERE harvest_source = 'gmail_outbound'
           AND is_active = 1
           AND (service_line = ? OR (? IS NULL AND service_line IS NULL))
         ORDER BY id DESC
         LIMIT 1
    """, (d['likely_service_line'], d['likely_service_line']))
    
    if harvested:
        print(f"--- PRAKASH SIR'S ACTUAL REPLY (library id={harvested['id']}) ---")
        actual_body = (harvested['content'] or '').strip()
        print(actual_body[:1500])
        if len(actual_body) > 1500:
            print(f"... [truncated, total {len(actual_body)} chars]")
    else:
        print("--- No matching harvested reply found ---")
    
    print()
    print()
