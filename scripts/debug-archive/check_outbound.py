"""
Read-only check: did Prakash sir already reply to any pending-approval
draft via Gmail directly?

Uses the existing Gmail credentials (no new auth, no permission changes,
no Anika state changes). Compares each draft's thread for a partner-sent
reply BEFORE we worry about Anika never being used.

Outputs:
  - pending Anika draft list
  - for each: was there a reply already in Gmail from prakasha@?
  - if yes: when, and content preview (first 200 chars)
  - summary at the bottom

Read only. Touches NOTHING.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.db import fetch_all, fetch_one
from app.tools import gmail_tool
from googleapiclient.errors import HttpError

# All pending drafts
pending = fetch_all("""
    SELECT d.id AS draft_id, d.created_at AS draft_created,
           re.id AS email_id, re.from_email,
           re.gmail_thread_id, re.received_at, re.subject
      FROM drafts d
      JOIN raw_emails re ON re.id = d.email_id
     WHERE d.sent_status = 'pending_approval'
     ORDER BY d.id DESC
""")

print(f"=" * 75)
print(f"Pending drafts: {len(pending)}")
print(f"Checking each thread for an outbound reply from prakasha@...")
print(f"=" * 75)
print()

# Get Gmail service
service = gmail_tool._service()
firm_email = "prakasha@balakrishnaandco.com"

results = []
for d in pending:
    thread_id = d["gmail_thread_id"]
    if not thread_id:
        results.append({"draft_id": d["draft_id"], "from": d["from_email"], "verdict": "NO_THREAD_ID", "detail": ""})
        continue

    try:
        thread = service.users().threads().get(userId="me", id=thread_id, format="metadata").execute()
        messages = thread.get("messages", [])
    except HttpError as e:
        results.append({"draft_id": d["draft_id"], "from": d["from_email"], "verdict": "GMAIL_ERROR", "detail": str(e)[:100]})
        continue

    # Find any message FROM prakasha@ in this thread
    partner_replies = []
    for m in messages:
        headers = {h["name"].lower(): h["value"] for h in m.get("payload", {}).get("headers", [])}
        from_header = headers.get("from", "")
        if firm_email in from_header.lower():
            partner_replies.append({
                "id": m["id"],
                "internalDate": m.get("internalDate"),
                "snippet": m.get("snippet", "")[:200],
            })

    if not partner_replies:
        verdict = "NO_REPLY_YET"
        detail = f"{len(messages)} messages in thread, none from partner"
    else:
        from datetime import datetime, timezone
        latest = partner_replies[-1]
        ts_ms = int(latest["internalDate"])
        sent_at = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        verdict = "PARTNER_REPLIED_VIA_GMAIL"
        detail = f"sent {sent_at.strftime('%Y-%m-%d %H:%M')} UTC | snippet: {latest['snippet'][:120]}"

    results.append({
        "draft_id": d["draft_id"],
        "from": d["from_email"],
        "subject": d["subject"][:50] if d["subject"] else "",
        "verdict": verdict,
        "detail": detail,
    })

# Print per-draft results
for r in results:
    print(f"  Draft {r['draft_id']:3d} from {r['from'][:30]:30s}")
    print(f"    Subject:  {r['subject']}")
    print(f"    Verdict:  {r['verdict']}")
    print(f"    Detail:   {r['detail']}")
    print()

# Summary
print("=" * 75)
print("SUMMARY")
print("=" * 75)
counts = {}
for r in results:
    counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
for verdict, n in counts.items():
    print(f"  {verdict}: {n}")
print()
if counts.get("PARTNER_REPLIED_VIA_GMAIL", 0) > 0:
    print(f"  → {counts['PARTNER_REPLIED_VIA_GMAIL']} drafts have already been replied to outside Anika.")
    print(f"     These drafts are stale; consider rejecting them in Anika and using")
    print(f"     the actual sent body as voice_examples for learning.")
else:
    print(f"  → No drafts have outbound replies yet. Anika is the only candidate.")
