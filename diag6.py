from app.db import fetch_all, fetch_one

# Find the most recent email from AK Sharma
email_row = fetch_one("SELECT id, from_email, subject FROM raw_emails WHERE subject LIKE '%Follow up on NRI%' ORDER BY id DESC LIMIT 1")
if not email_row:
    print("Test email not found in DB")
else:
    eid = email_row['id']
    print(f"Email ID: {eid}")
    print(f"From: {email_row['from_email']}")
    print(f"Subject: {email_row['subject']}")
    print()
    
    # All agent runs for this email
    runs = fetch_all("SELECT agent_name, status, error_text, latency_ms, prompt_version FROM reasoning_log WHERE email_id=? ORDER BY id", (eid,))
    print(f"Agent runs: {len(runs)}")
    for r in runs:
        print(f"  {r['agent_name']:15} status={r['status']:8} latency={r['latency_ms']}ms prompt_v={r['prompt_version']}")
        if r['error_text']: print(f"    ERROR: {r['error_text']}")
    print()
    
    # Classification
    cls = fetch_one("SELECT category, confidence FROM classifications WHERE email_id=?", (eid,))
    print(f"Classification: {cls}")
    
    # Enrichment
    enr = fetch_one("SELECT likely_service_line, urgency, routing_partner FROM enrichments WHERE email_id=?", (eid,))
    print(f"Enrichment: {enr}")
    
    # Draft
    drf = fetch_one("SELECT id, subject FROM drafts WHERE email_id=?", (eid,))
    print(f"Draft: {drf}")
