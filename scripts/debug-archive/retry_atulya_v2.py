import asyncio
import os
os.environ["ANIKA_TEST_MODE"] = "true"

from app.db import fetch_one
from app.agents import orchestrator
from app.tools.gmail_tool import InboxMessage

async def main():
    email = fetch_one("SELECT * FROM raw_emails WHERE id = 875")
    if not email:
        print("Email 875 not found")
        return

    print(f"Re-processing email 875: {email['from_email']}")
    print(f"  Subject: {email['subject']}")
    print(f"  ANIKA_TEST_MODE={os.environ.get('ANIKA_TEST_MODE')}")
    print()

    # Show fields available on the row
    print("Available fields on raw_emails:")
    for k in email.keys():
        print(f"  {k}")
    print()

    # Construct InboxMessage. Try the most likely shape first.
    # InboxMessage typically has: id, thread_id, from_email, from_name,
    # subject, body_plain, body_html, received_at, has_attachments
    try:
        msg = InboxMessage(
            id=email["gmail_message_id"] if "gmail_message_id" in email.keys() else f"local-875",
            thread_id=email["thread_id"] if "thread_id" in email.keys() else None,
            from_email=email["from_email"],
            from_name=email["from_name"] or "",
            subject=email["subject"] or "",
            body_plain=email["body_plain"] or "",
            body_html=email["body_html"] if "body_html" in email.keys() else "",
            received_at=email["received_at"],
            has_attachments=False,
        )
    except TypeError as e:
        print(f"InboxMessage signature mismatch: {e}")
        # Show actual signature
        import inspect
        print()
        print("InboxMessage signature:")
        print(inspect.signature(InboxMessage))
        return

    try:
        result = await orchestrator.handle(msg)
        print(f"orchestrator.handle COMPLETED: {result}")
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
