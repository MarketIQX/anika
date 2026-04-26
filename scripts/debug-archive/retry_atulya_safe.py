import asyncio
import os
# Force test mode for this run only — skips mark_as_processed
os.environ["ANIKA_TEST_MODE"] = "true"

from app.db import fetch_one
from app.agents import orchestrator

async def main():
    email = fetch_one("SELECT * FROM raw_emails WHERE id = 875")
    if not email:
        print("Email 875 not found")
        return

    print(f"Re-processing email 875: {email['from_email']}")
    print(f"  Subject: {email['subject']}")
    print(f"  ANIKA_TEST_MODE={os.environ.get('ANIKA_TEST_MODE')}")
    print()

    # Build msg dict for orchestrator
    msg = {
        "id": email["gmail_message_id"] if "gmail_message_id" in email.keys() else f"local-{email['id']}",
        "threadId": email["thread_id"] if "thread_id" in email.keys() else None,
        "from_email": email["from_email"],
        "from_name": email["from_name"],
        "subject": email["subject"],
        "body_plain": email["body_plain"],
        "received_at": email["received_at"],
        "raw_email_id": email["id"],
    }

    try:
        await orchestrator.handle(msg)
        print("orchestrator.handle COMPLETED")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

    print()
    draft = fetch_one("SELECT id, sent_status, created_at FROM drafts WHERE email_id = 875")
    if draft:
        print(f"DRAFT CREATED: id={draft['id']}, status={draft['sent_status']}")
    else:
        print("Still no draft")

asyncio.run(main())
