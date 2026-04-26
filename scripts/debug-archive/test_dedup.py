import asyncio
from app.db import execute, fetch_all
from app.agents.duplicate_judge import judge_duplicate

async def main():
    # Clean any stale test rules first
    execute("DELETE FROM meta_rules WHERE created_by = 'test_dedup'")

    # Seed ONE rule from our earlier meta-rule test (external security warnings)
    execute("""
        INSERT INTO meta_rules
            (rule_text, trigger_pattern, target_purpose, target_service_line, priority, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "Security warnings from external parties (banks, vendors) are reference_material, not firm_policy — firm_policy refers only to guidelines authored by Balakrishna & Co.",
        "Content contains security warnings, rules, or advice issued by external entities, such as banks or vendors, rather than internal firm policies.",
        "reference_material",
        None,
        5,
        "test_dedup",
    ))
    seeded = fetch_all("SELECT id FROM meta_rules WHERE created_by = 'test_dedup' ORDER BY id DESC LIMIT 1")
    seeded_id = seeded[0]["id"]
    print(f"Seeded rule id={seeded_id}")
    print()

    # Test 1 — Actual duplicate (same principle, different wording)
    print("=" * 90)
    print("TEST 1 — Actual duplicate (same principle, different wording)")
    print("=" * 90)
    j1 = await judge_duplicate(
        new_rule_text="Warnings issued by third-party entities like banks are reference_material, not firm_policy",
        new_trigger="Content is a rule or warning written by a bank, vendor, or other non-firm entity",
        new_target_purpose="reference_material",
    )
    print(f"is_duplicate: {j1.is_duplicate}")
    print(f"duplicate_of_id: {j1.duplicate_of_id}")
    print(f"reasoning: {j1.reasoning}")
    if j1.difference_if_similar:
        print(f"difference: {j1.difference_if_similar}")
    expected = "DUPLICATE" if j1.is_duplicate else "NOT duplicate"
    print(f">>> Expected: DUPLICATE. Got: {expected}")
    print()

    # Test 2 — Similar wording, DIFFERENT principle (filtering by staleness, not authorship)
    print("=" * 90)
    print("TEST 2 — Similar wording, DIFFERENT principle (staleness vs authorship)")
    print("=" * 90)
    j2 = await judge_duplicate(
        new_rule_text="Outdated notifications and archived content older than 12 months are reference_material",
        new_trigger="Content is a notification, advisory, or communication that has aged beyond 12 months",
        new_target_purpose="reference_material",
    )
    print(f"is_duplicate: {j2.is_duplicate}")
    print(f"duplicate_of_id: {j2.duplicate_of_id}")
    print(f"reasoning: {j2.reasoning}")
    if j2.difference_if_similar:
        print(f"difference: {j2.difference_if_similar}")
    expected = "NOT duplicate" if not j2.is_duplicate else "WRONGLY marked duplicate"
    print(f">>> Expected: NOT duplicate. Got: {expected}")
    print()

    # Test 3 — Completely different rule (should obviously not be duplicate)
    print("=" * 90)
    print("TEST 3 — Completely different rule (different purpose entirely)")
    print("=" * 90)
    j3 = await judge_duplicate(
        new_rule_text="Lists of transaction codes from bank statements are document_type, teaching Anika document anatomy",
        new_trigger="Content is a structured list of transaction codes or field legends",
        new_target_purpose="document_type",
    )
    print(f"is_duplicate: {j3.is_duplicate}")
    print(f"duplicate_of_id: {j3.duplicate_of_id}")
    print(f"reasoning: {j3.reasoning}")
    expected = "NOT duplicate" if not j3.is_duplicate else "WRONGLY marked duplicate"
    print(f">>> Expected: NOT duplicate. Got: {expected}")
    print()

    # Cleanup
    execute("DELETE FROM meta_rules WHERE created_by = 'test_dedup'")
    print("(Cleaned up test rules)")

asyncio.run(main())
