from app.db import execute, fetch_one
import asyncio
from app.cognitive import teaching

# Queue 12: status=approved but no library entry. Reset it back so we can re-finalize.
# Use finalize_with_purpose to create the library entry this time.
async def main():
    # Reset queue 12 so finalize_with_purpose can run (it doesnt have the status guard)
    # Actually finalize_with_purpose doesn't check status — so just run it
    q12 = fetch_one("SELECT id, raw_content, anika_proposed_purpose FROM teaching_queue WHERE id=12")
    if q12:
        print(f"Queue 12 content: {q12['raw_content'][:60]}...")
        print(f"Anika proposed: {q12['anika_proposed_purpose']}")

        result = await teaching.finalize_with_purpose(
            12,
            confirmed_purpose="firm_policy",
            service_line=None,
            created_by="aks@marketiqx.com",
        )
        print(f"Result: {result}")
    else:
        print("Queue 12 not found")

    # Queues 10, 11 are orphaned pending rows with no classification
    # Delete them (they're just noise)
    execute("DELETE FROM teaching_queue WHERE id IN (10, 11) AND anika_proposed_purpose IS NULL")
    print("Cleaned up stuck queues 10, 11")

asyncio.run(main())
