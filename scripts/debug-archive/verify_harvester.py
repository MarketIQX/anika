"""Verify the outbound harvester actually ran and what it did."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from app.db import fetch_all, fetch_one

print("=" * 70)
print("OUTBOUND HARVESTER STATE")
print("=" * 70)
print()

# Did the harvester ever log a successful run?
print("Recent harvester activity in reasoning_log:")
runs = fetch_all("""
    SELECT id, status, output_json, reasoning_text, created_at
      FROM reasoning_log
     WHERE agent_name = 'outbound_harvester'
     ORDER BY id DESC LIMIT 10
""")
print(f"  Total entries: {len(runs)}")
for r in runs:
    print(f"  {r['created_at'][:19]} | status={r['status']} | {(r['reasoning_text'] or '')[:80]}")

print()
print("=" * 70)
print("VOICE LIBRARY — by harvest source")
print("=" * 70)
sources = fetch_all("""
    SELECT harvest_source, COUNT(*) AS n
      FROM knowledge_library
     WHERE is_active = 1
       AND purpose = 'voice_example'
     GROUP BY harvest_source
""")
for s in sources:
    src = s['harvest_source'] or '(NULL — pre-1C-3 legacy)'
    print(f"  {src}: {s['n']}")

print()
print("=" * 70)
print("HARVESTED VOICE EXAMPLES — full attribution")
print("=" * 70)
voices = fetch_all("""
    SELECT id, service_line, harvest_source, created_by, applied_count, last_used_at,
           substr(content, 1, 150) AS preview, created_at
      FROM knowledge_library
     WHERE is_active = 1
       AND purpose = 'voice_example'
       AND harvest_source = 'gmail_outbound'
     ORDER BY id DESC
""")
print(f"  Total harvested via Gmail: {len(voices)}")
for v in voices:
    print()
    print(f"  Library id={v['id']} | service_line={v['service_line'] or '(universal)'}")
    print(f"    by: {v['created_by']}")
    print(f"    saved: {v['created_at'][:19]}")
    print(f"    preview: {v['preview']}")

print()
print("=" * 70)
print("RAW EMAILS — outbound harvest scan state (last 7 days)")
print("=" * 70)
emails = fetch_all("""
    SELECT id, from_email, gmail_thread_id, 
           outbound_reply_gmail_id, outbound_reply_harvested_at,
           subject
      FROM raw_emails
     WHERE gmail_thread_id IS NOT NULL
       AND julianday('now') - julianday(received_at) < 7
     ORDER BY id DESC LIMIT 20
""")

scanned = 0
not_scanned = 0
harvested = 0
for e in emails:
    has_reply_id = e['outbound_reply_gmail_id'] is not None
    has_harvest_time = e['outbound_reply_harvested_at'] is not None
    
    if has_reply_id:
        scanned += 1
        harvested += 1
        marker = "HARVESTED"
    elif has_harvest_time:
        scanned += 1
        marker = "scanned-no-outbound"
    else:
        not_scanned += 1
        marker = "not-yet-scanned"
    
    sender = (e['from_email'] or '')[:30]
    print(f"  email {e['id']:3d} | {marker:20s} | {sender}")

print()
print(f"Summary:")
print(f"  Total emails (last 7 days, with thread_id): {len(emails)}")
print(f"  Scanned: {scanned}")
print(f"  Not yet scanned: {not_scanned}")
print(f"  Harvested: {harvested}")

print()
print("=" * 70)
print("DRAFTS BYPASSED — partner replied via Gmail directly")
print("=" * 70)
bypassed = fetch_all("""
    SELECT d.id, d.created_at, re.from_email, e.likely_service_line
      FROM drafts d
      JOIN raw_emails re ON re.id = d.email_id
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE d.sent_status = 'rejected_partner_replied_outside'
     ORDER BY d.id DESC
""")
print(f"  Total: {len(bypassed)}")
for b in bypassed:
    sl = (b['likely_service_line'] or '-')
    print(f"  draft {b['id']:3d} | {sl:20s} | {b['from_email']}")
