from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Now: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

# Pull every sent_log row
print("=" * 70)
print("ALL sent_log entries — what emails has Anika actually sent?")
print("=" * 70)
sent_rows = fetch_all("""
    SELECT id, draft_id, email_id, approval_id, gmail_message_id,
           to_email, subject, sent_at, test_mode
      FROM sent_log
     ORDER BY sent_at DESC
""")
print(f"Total sent_log rows: {len(sent_rows)}")
print()
for s in sent_rows:
    print(f"  sent_log id={s['id']}")
    print(f"    sent_at:    {s['sent_at']}")
    print(f"    draft_id:   {s['draft_id']}")
    print(f"    to_email:   {s['to_email']}")
    print(f"    subject:    {s['subject']}")
    print(f"    test_mode:  {s['test_mode']}")
    print(f"    gmail_msg_id: {s['gmail_message_id'] or '-'}")
    print()

# Pull all drafts with status='sent'
print("=" * 70)
print("DRAFTS with sent_status='sent'")
print("=" * 70)
sent_drafts = fetch_all("""
    SELECT d.id, d.subject, d.created_at, d.updated_at,
           re.from_email AS recipient
      FROM drafts d
      LEFT JOIN raw_emails re ON re.id = d.email_id
     WHERE d.sent_status = 'sent'
""")
print(f"Drafts with sent status: {len(sent_drafts)}")
for d in sent_drafts:
    print(f"  draft {d['id']}: to {d['recipient']}, updated {d['updated_at']}")

# All approvals with decision='approve'
print()
print("=" * 70)
print("APPROVALS — every approve decision")
print("=" * 70)
approvals = fetch_all("""
    SELECT a.id, a.draft_id, a.decision, a.decided_by, a.created_at
      FROM approvals a
     WHERE a.decision = 'approve'
     ORDER BY a.created_at DESC
""")
print(f"Approve decisions: {len(approvals)}")
for a in approvals:
    by = (a['decided_by'] or '?').split('@')[0]
    print(f"  approval id={a['id']}, draft_id={a['draft_id']}, by {by} at {a['created_at'][:19]}")

# Recent access_log activity that could indicate the second send
print()
print("=" * 70)
print("Recent draft_approve actions in access_log")
print("=" * 70)
acts = fetch_all("""
    SELECT created_at, user_email, action, target
      FROM access_log
     WHERE action LIKE 'draft_approve%' OR action LIKE '%send%'
     ORDER BY id DESC LIMIT 10
""")
for a in acts:
    user = (a['user_email'] or 'anon').split('@')[0]
    print(f"  {a['created_at'][:19]} | {user:12s} | {a['action']:20s} | {a['target'] or '-'}")
