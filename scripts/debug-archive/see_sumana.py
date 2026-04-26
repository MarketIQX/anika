from app.db import fetch_one, fetch_all

# Sumana's email
e = fetch_one("""
    SELECT id, from_email, subject, body_plain, snippet, received_at
      FROM raw_emails WHERE from_email LIKE '%sumana%' ORDER BY id DESC LIMIT 1
""")
if not e:
    print("Sumana email not found")
else:
    print(f"Email id: {e['id']}")
    print(f"From: {e['from_email']}")
    print(f"Subject: {e['subject']}")
    print(f"Received: {e['received_at']}")
    print(f"Body length: {len(e['body_plain'] or '')}")
    print()
    print("FULL BODY:")
    print("=" * 70)
    print(e['body_plain'])
    print("=" * 70)

    # What did the classifier say (if anything)?
    print()
    cls = fetch_one("SELECT category, confidence, reasoning FROM classifications WHERE email_id = ?", (e['id'],))
    if cls:
        print(f"Classifier: {cls['category']} (conf={cls['confidence']})")
        print(f"  Reasoning: {cls['reasoning']}")
    else:
        print("No classification recorded")

    # Was a draft attempted?
    d = fetch_one("SELECT id, sent_status FROM drafts WHERE email_id = ?", (e['id'],))
    if d:
        print(f"Draft: id={d['id']}, status={d['sent_status']}")
    else:
        print("No draft created")

    # Last enricher attempt
    enr = fetch_one("""
        SELECT status, error_text, created_at, latency_ms
          FROM reasoning_log
         WHERE agent_name = 'enricher' AND email_id = ?
         ORDER BY id DESC LIMIT 1
    """, (e['id'],))
    if enr:
        print()
        print(f"Last enricher attempt: status={enr['status']}, latency={enr['latency_ms']}ms")
        print(f"  Error: {(enr['error_text'] or '-')[:200]}")
