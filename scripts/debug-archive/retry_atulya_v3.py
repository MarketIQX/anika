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
    print()

    msg = InboxMessage(
        message_id=email["gmail_message_id"],
        thread_id=email["gmail_thread_id"] or "",
        from_email=email["from_email"],
        from_name=email["from_name"] or "",
        to_email=email["to_email"] or "",
        cc=email["cc"] or "",
        subject=email["subject"] or "",
        body_plain=email["body_plain"] or "",
        body_html=email["body_html"] or "",
        snippet=email["snippet"] or "",
        received_at=email["received_at"] or "",
        is_reply_in_thread=bool(email["is_reply_in_thread"]),
    )

    try:
        result = await orchestrator.handle(msg)
        print(f"orchestrator.handle COMPLETED")
        print(f"  result: {result}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

    print()
    draft = fetch_one("""
        SELECT id, sent_status, subject, substr(body, 1, 200) body_preview, created_at
          FROM drafts WHERE email_id = 875
    """)
    if draft:
        print(f"DRAFT CREATED:")
        print(f"  id:      {draft['id']}")
        print(f"  status:  {draft['sent_status']}")
        print(f"  subject: {draft['subject']}")
        print(f"  body preview:")
        print(f"  {draft['body_preview']}")
    else:
        print("Still no draft")
        # Check enricher status for diagnosis
        enr = fetch_one("""
            SELECT status, error_text
              FROM reasoning_log
             WHERE agent_name = 'enricher' AND email_id = 875
             ORDER BY id DESC LIMIT 1
        """)
        if enr:
            print(f"  Enricher: status={enr['status']}, error={(enr['error_text'] or '-')[:100]}")

asyncio.run(main())
