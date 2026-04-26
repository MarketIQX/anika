import asyncio
import traceback
from app.db import fetch_one
from app.agents import purpose_classifier, humility_layer
from app.dashboard import routes as _r

async def simulate():
    # Simulate what the route does for queue id=12 (latest one)
    queue_row = fetch_one("SELECT * FROM teaching_queue WHERE id = 12")
    print("Queue row exists:", queue_row is not None)
    if queue_row:
        print("Raw content preview:", (queue_row["raw_content"] or "")[:100])

    # Step 1 — call classifier
    try:
        print()
        print("Calling purpose_classifier...")
        proposal = await purpose_classifier.classify_purpose(
            content=queue_row["raw_content"],
            filename=None,
            file_mime=None,
        )
        print("Classifier returned:")
        print(f"  purpose: {proposal.proposed_purpose}")
        print(f"  confidence: {proposal.confidence}")
        print(f"  reasoning: {proposal.reasoning[:80]}")
    except Exception as e:
        print(f"CLASSIFIER FAILED: {e}")
        traceback.print_exc()
        return

    # Step 2 — call humility if low confidence
    if proposal.confidence < 0.5:
        try:
            print("Calling humility_layer...")
            articulation = await humility_layer.articulate_uncertainty(
                content=queue_row["raw_content"],
                classifier_reasoning=proposal.reasoning,
            )
            print("Humility returned features:", articulation.noticed_features[:2])
        except Exception as e:
            print(f"HUMILITY FAILED: {e}")
            traceback.print_exc()
            return
    else:
        print("Skipping humility (confidence >= 0.5)")

    # Step 3 — UPDATE query
    from app.db import execute
    import json
    try:
        print()
        print("Running UPDATE...")
        execute(
            """
            UPDATE teaching_queue SET
                anika_proposed_purpose = ?,
                anika_proposed_confidence = ?,
                anika_reasoning = ?,
                anika_suggested_sl = ?,
                anika_suggested_custom = ?,
                humility_articulation = ?,
                status = ?,
                awaiting_confirmation = 1
             WHERE id = ?
            """,
            (
                proposal.proposed_purpose,
                proposal.confidence,
                proposal.reasoning,
                proposal.suggested_service_line,
                proposal.suggested_custom_label,
                None,
                "processing",
                12,
            ),
        )
        print("UPDATE succeeded")
    except Exception as e:
        print(f"UPDATE FAILED: {e}")
        traceback.print_exc()

asyncio.run(simulate())
