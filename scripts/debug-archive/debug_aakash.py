from app.db import fetch_one, fetch_all

print("=" * 70)
print("AAKASH — email 881 — what happened?")
print("=" * 70)
e = fetch_one("SELECT * FROM raw_emails WHERE id = 881")
if not e:
    print("  Email 881 not found in raw_emails")
else:
    print(f"  from: {e['from_email']}")
    print(f"  subject: {e['subject']}")
    print(f"  received: {e['received_at']}")
    print(f"  is_web_form: {e['is_web_form']}")
    print()
    print(f"  body (first 500 chars):")
    print(f"  {(e['body_plain'] or '')[:500]}")
    print()

    # Classifier
    cls = fetch_one("SELECT category, confidence, reasoning FROM classifications WHERE email_id = 881")
    if cls:
        print(f"  Classifier: {cls['category']} (conf={cls['confidence']})")
        print(f"  Reasoning: {(cls['reasoning'] or '')[:300]}")
    else:
        print(f"  Classifier: NO ROW")

    # All reasoning_log entries for this email
    print()
    print(f"  ALL reasoning_log entries for email 881:")
    logs = fetch_all("""
        SELECT id, agent_name, status, error_text, created_at
          FROM reasoning_log
         WHERE email_id = 881
         ORDER BY id ASC
    """)
    for l in logs:
        err = (l['error_text'] or '')[:200]
        print(f"    {l['created_at'][11:19]} | {l['agent_name']:15s} | status={l['status']}")
        if err:
            print(f"      error: {err}")

    # Did a draft get created?
    print()
    draft = fetch_one("SELECT id, sent_status, created_at FROM drafts WHERE email_id = 881")
    if draft:
        print(f"  Draft: {draft['id']}, status={draft['sent_status']}, at {draft['created_at']}")
    else:
        print(f"  Draft: NONE")

    # Check if email has been marked processed in Gmail (look for orchestrator logs)
    orch_logs = fetch_all("""
        SELECT output_json, reasoning_text, created_at
          FROM reasoning_log
         WHERE agent_name = 'orchestrator' AND email_id = 881
         ORDER BY id DESC
    """)
    print()
    print(f"  Orchestrator decisions: {len(orch_logs)}")
    for o in orch_logs:
        print(f"    {o['created_at'][11:19]}: {(o['output_json'] or '')[:250]}")
        print(f"      reasoning: {(o['reasoning_text'] or '')[:200]}")

# Also check Sumana for comparison
print()
print("=" * 70)
print("SUMANA — email 877 — for comparison")
print("=" * 70)
sumana_draft = fetch_one("SELECT id, sent_status FROM drafts WHERE email_id = 877")
if sumana_draft:
    print(f"  Draft: {sumana_draft['id']}, status={sumana_draft['sent_status']}")
else:
    print(f"  Draft: NONE (still stuck — original Enricher crash, never retried in production)")

# Show overall draft creation timeline today
print()
print("=" * 70)
print("DRAFTS CREATED TODAY (last 24h)")
print("=" * 70)
today_drafts = fetch_all("""
    SELECT d.id, d.sent_status, d.created_at, e.likely_service_line, re.from_email
      FROM drafts d
      LEFT JOIN raw_emails re ON re.id = d.email_id
      LEFT JOIN enrichments e ON e.email_id = d.email_id
     WHERE julianday('now') - julianday(d.created_at) < 1
     ORDER BY d.id DESC
""")
print(f"  {len(today_drafts)} drafts created in last 24h")
for d in today_drafts:
    print(f"    draft {d['id']:3d} | {d['sent_status']:20s} | {d['created_at'][:19]} | {(d['likely_service_line'] or '-'):20s} | {d['from_email']}")
