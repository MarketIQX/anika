from app.db import fetch_one, fetch_all

# Was email 876 drafted?
print("=" * 70)
print("EMAIL 876 (hemajenne) — was it drafted?")
print("=" * 70)
draft = fetch_one("""
    SELECT id, sent_status, cognitive_state, voice_coverage_count,
           subject, substr(body, 1, 200) body_preview, created_at
      FROM drafts WHERE email_id = 876
""")
if draft:
    print(f"  Draft id: {draft['id']}")
    print(f"  Status: {draft['sent_status']}")
    print(f"  Cognitive state: {draft['cognitive_state']}")
    print(f"  Voice count: {draft['voice_coverage_count']}")
    print(f"  Subject: {draft['subject']}")
    print(f"  Body preview:")
    print(f"    {draft['body_preview']}")
else:
    print("  NO draft — Anika has not yet processed this email")
    # Check if enricher ran
    enr = fetch_one("""
        SELECT status, error_text, created_at
          FROM reasoning_log
         WHERE agent_name = 'enricher' AND email_id = 876
         ORDER BY id DESC LIMIT 1
    """)
    if enr:
        print(f"  Enricher attempted: status={enr['status']}, error={(enr['error_text'] or '-')[:100]}")
    else:
        print("  Enricher has not run on this email yet")

# What does email 876 actually say?
print()
print("Email 876 body:")
print("-" * 70)
e = fetch_one("SELECT body_plain, subject FROM raw_emails WHERE id = 876")
if e:
    print(f"Subject: {e['subject']}")
    print(f"Body:")
    print(e['body_plain'])
