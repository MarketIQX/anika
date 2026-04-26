import asyncio
from app.db import fetch_all
from app.agents.purpose_classifier import classify_purpose

async def main():
    entries = fetch_all("""
        SELECT id, content, purpose AS our_classification
        FROM knowledge_library WHERE is_active=1 ORDER BY id
    """)

    print("=" * 120)
    print("LIVE TEST — Purpose Classifier vs Manual Migration")
    print("=" * 120)
    print(f"{'id':>3} | {'Our label':<22s} | {'Anika proposed':<22s} | {'conf':>5s} | {'match':<5s} | reasoning")
    print("-" * 120)

    match_count = 0
    total = 0
    results = []
    for e in entries:
        try:
            proposal = await classify_purpose(content=e["content"], filename=None, file_mime=None)
            match = "YES" if proposal.proposed_purpose == e["our_classification"] else "NO"
            if match == "YES":
                match_count += 1
            total += 1
            results.append({
                "id": e["id"],
                "ours": e["our_classification"],
                "anika": proposal.proposed_purpose,
                "conf": proposal.confidence,
                "match": match,
                "reasoning": proposal.reasoning[:80],
            })
            print(f"{e['id']:>3} | {e['our_classification']:<22s} | {proposal.proposed_purpose:<22s} | {proposal.confidence:5.2f} | {match:<5s} | {proposal.reasoning[:80]}")
        except Exception as ex:
            print(f"{e['id']:>3} | ERROR: {str(ex)[:80]}")

    print("-" * 120)
    if total > 0:
        accuracy = match_count / total * 100
        print(f"Accuracy: {match_count}/{total} = {accuracy:.1f}%")

asyncio.run(main())
