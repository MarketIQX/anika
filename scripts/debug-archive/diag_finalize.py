import asyncio
import traceback
from app.cognitive import teaching
from app.db import fetch_one, execute, fetch_all

async def main():
    q = fetch_one("SELECT * FROM teaching_queue WHERE id = 12")
    print("Queue 12:")
    print(f"  status: {q['status']}")
    print(f"  awaiting: {q['awaiting_confirmation']}")
    print(f"  anika_proposed: {q['anika_proposed_purpose']}")
    print()

    # Reset queue 12 status so we can retry
    execute("UPDATE teaching_queue SET status=? WHERE id=?", ("processing", 12))
    print("Reset queue 12 to processing, now calling finalize_queue...")

    try:
        result = await teaching.finalize_queue(12)
        print("finalize_queue returned:", result)
    except Exception as e:
        print(f"FAILED: {e}")
        traceback.print_exc()

    # Check if library entry was created
    print()
    print("Latest library entries:")
    rows = fetch_all("""
        SELECT id, purpose, user_confirmed_purpose, content, source_queue_id
          FROM knowledge_library WHERE is_active=1 ORDER BY id DESC LIMIT 3
    """)
    for r in rows:
        print(f"  id={r['id']} purpose={r['purpose']} queue_id={r['source_queue_id']}: {(r['content'] or '')[:60]}")

asyncio.run(main())
