import asyncio
import os
os.environ["ANIKA_TEST_MODE"] = "true"

from app.db import fetch_one
from app.agents import orchestrator
from app.tools.gmail_tool import InboxMessage

async def retry(email_id: int, label: str):
    """Manually retrigger an email through the new tool-less Enricher."""
    print(f"\n{'='*70}")
    print(f"Retrying {label} (email {email_id})")
    print(f"{'='*70}")

    email = fetch_one("SELECT * FROM raw_emails WHERE id = ?", (email_id,))
    if not email:
        print(f"  Email {email_id} not found")
        return

    print(f"  from: {email['from_email']}")
    print(f"  subject: {email['subject']}")
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

    import time
    start = time.time()
    try:
        result = await orchestrator.handle(msg)
        elapsed = time.time() - start
        print(f"  COMPLETED in {elapsed:.1f}s")
        print(f"  Result: {result}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    draft = fetch_one("SELECT id, sent_status, cognitive_state, voice_coverage_count FROM drafts WHERE email_id = ?", (email_id,))
    if draft:
        print(f"  DRAFT CREATED: id={draft['id']}, state={draft['cognitive_state']}, vcc={draft['voice_coverage_count']}, status={draft['sent_status']}")
    else:
        print(f"  No draft created")

async def main():
    await retry(881, "Aakash")
    await retry(877, "Sumana")

asyncio.run(main())
