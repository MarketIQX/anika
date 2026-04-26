from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

print("=" * 80)
print(f"QC CHECK — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 80)

# ============================================================
# 1. DRAFT 25 (MANGLAM) — signature fixed?
# ============================================================
print()
print("=" * 80)
print("1. DRAFT 25 (MANGLAM) — SIGNATURE CHECK")
print("=" * 80)
d = fetch_one("SELECT id, body, sent_status, updated_at FROM drafts WHERE id = 25")
print(f"  Status: {d['sent_status']}")
print(f"  Last updated: {d['updated_at']}")
print()
body = d['body'] or ''
print(f"  Full body ({len(body)} chars):")
print("-" * 80)
print(body)
print("-" * 80)

# Signature marker count
print()
print("  Signature marker analysis:")
for marker in ["Warm regards,", "Yours faithfully,", "Best regards,", "Sincerely,",
               "S V Prakasha", "CA Prakasha", "Wilson Garden"]:
    count = body.count(marker)
    status = "OK" if count <= 1 else "DUPLICATE"
    print(f"    {status:10s} '{marker}' appears {count} time(s)")

# ============================================================
# 2. WAS THIS A NEW DRAFTING OR LEARNING?
# ============================================================
print()
print("=" * 80)
print("2. IS THIS A FRESH SCENARIO OR HAS ANIKA SEEN THIS BEFORE?")
print("=" * 80)

# The original email that triggered Draft 25
d25 = fetch_one("""
    SELECT d.email_id, d.created_at AS draft_time, re.from_email, re.subject, re.body_plain, re.received_at
      FROM drafts d
      LEFT JOIN raw_emails re ON re.id = d.email_id
     WHERE d.id = 25
""")
if d25:
    print(f"  Original sender: {d25['from_email']}")
    print(f"  Original subject: {d25['subject']}")
    print(f"  Received at: {d25['received_at']}")
    print(f"  Draft made at: {d25['draft_time']}")
    print()
    print(f"  Original email body (first 300 chars):")
    print(f"    {(d25['body_plain'] or '')[:300]}")

# Has Anika drafted for this service line before?
print()
print("  Previous drafts for foreign_subsidiary service_line:")
prior = fetch_all("""
    SELECT d.id, d.sent_status, d.created_at, e.likely_service_line, re.from_email
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
      LEFT JOIN raw_emails re ON re.id = d.email_id
     WHERE e.likely_service_line = 'foreign_subsidiary'
       AND d.id < 25
     ORDER BY d.id DESC LIMIT 5
""")
if prior:
    for p in prior:
        print(f"    draft {p['id']:3d} | {p['sent_status']:20s} | {p['from_email']} | {p['created_at'][:19]}")
else:
    print("    None — this is Anika's FIRST foreign_subsidiary draft")

# ============================================================
# 3. DID DRAFT 25 USE LEARNED VOICE OR OLD TRAINING?
# ============================================================
print()
print("=" * 80)
print("3. WHAT DID DRAFT 25 LEARN FROM?")
print("=" * 80)
# Drafter reasoning_log for draft 25
log = fetch_one("""
    SELECT reasoning_text, input_json, output_json, created_at
      FROM reasoning_log
     WHERE agent_name = 'drafter'
       AND draft_id = 25
     ORDER BY id DESC LIMIT 1
""")
if log:
    print(f"  Drafter reasoning at {log['created_at']}:")
    print(f"    {log['reasoning_text']}")
    print()
    # Parse input_json to find which library items were retrieved
    import json
    try:
        inp = json.loads(log['input_json'])
        # Look for retrieved items
        for key in ['retrieved_rules', 'retrieved_examples', 'retrieved_facts',
                    'rule_ids', 'example_ids', 'fact_ids', 'used_library_ids']:
            if key in inp:
                print(f"  {key}: {inp[key]}")
    except Exception:
        # Print raw snippet
        print(f"  input_json (first 500 chars):")
        print(f"    {(log['input_json'] or '')[:500]}")
else:
    print("  No drafter reasoning_log entry for draft 25")

# Also check voice_example usage
print()
print("  Voice_example usage counts (applied_count):")
voices = fetch_all("""
    SELECT id, service_line, applied_count, last_used_at, substr(content, 1, 60) preview
      FROM knowledge_library
     WHERE is_active = 1 AND purpose = 'voice_example'
""")
for v in voices:
    print(f"    id={v['id']} | {v['service_line'] or '-':20s} | used={v['applied_count']} times | last_used={v['last_used_at']}")
    print(f"         {v['preview']}")

# ============================================================
# 4. OLD EXEMPLARS — STILL BEING USED?
# ============================================================
print()
print("=" * 80)
print("4. DID ANIKA PULL FROM LEGACY MEMORY EXEMPLARS?")
print("=" * 80)
# Count tokens in memory exemplars that match draft 25 content
mem = fetch_all("""
    SELECT id, subject, substr(content, 1, 100) preview
      FROM memory
     WHERE kind = 'exemplar'
""")
draft_text = body.lower()
for m in mem:
    preview_words = (m['preview'] or '').lower().split()[:10]
    # Check if any distinctive phrase appears in draft
    matches = sum(1 for w in preview_words if len(w) > 6 and w in draft_text)
    if matches >= 2:
        print(f"    memory id={m['id']} ({m['subject']}) — POSSIBLE SOURCE ({matches} word matches)")
        print(f"      {m['preview']}")
