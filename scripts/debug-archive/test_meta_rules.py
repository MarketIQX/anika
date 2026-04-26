import asyncio
from app.agents.meta_rule_generator import generate_meta_rule

# The 4 misclassifications from the earlier live test
corrections = [
    {
        "id": 8,
        "content": "Never share your OTP, CVV or passwords with anyone, even if the person claims to be a Bank employee.",
        "anika_proposed": "firm_policy",
        "user_confirmed": "reference_material",
    },
    {
        "id": 12,
        "content": "Transaction Types Include: RCHG - Recharge, DTAX - Direct Tax, BPAY - Bill payment, IDTX - Indirect Tax, BBPS - Bill payment system",
        "anika_proposed": "reference_material",
        "user_confirmed": "document_type",
    },
    {
        "id": 16,
        "content": "Never share your OTP, CVV or passwords with anyone, even if the person claims to be a Bank employee.",
        "anika_proposed": "firm_policy",
        "user_confirmed": "reference_material",
    },
    {
        "id": 19,
        "content": "List of transaction legends: RCHG, DTAX, BPAY, IDTX, BBPS, INFT, BIL, ONL, NEFT, PAVC, PAC, LNPY, CC",
        "anika_proposed": "reference_material",
        "user_confirmed": "document_type",
    },
]

async def main():
    print("=" * 100)
    print("META-RULE GENERATION TEST — Can Anika generalize corrections?")
    print("=" * 100)
    for c in corrections:
        print()
        print(f"--- Correction id={c['id']} ---")
        print(f"Content: {c['content'][:80]}...")
        print(f"Anika proposed: {c['anika_proposed']}  →  User confirmed: {c['user_confirmed']}")
        try:
            rule = await generate_meta_rule(
                content=c["content"],
                anika_proposed=c["anika_proposed"],
                user_confirmed=c["user_confirmed"],
            )
            print()
            print(f"GENERATED RULE (confidence: {rule.confidence:.2f}):")
            print(f"  Rule text: {rule.rule_text}")
            print(f"  Trigger:   {rule.trigger_pattern}")
            print(f"  Target:    {rule.target_purpose}")
            if rule.target_service_line:
                print(f"  SL:        {rule.target_service_line}")
            print(f"  Reasoning: {rule.reasoning}")
        except Exception as e:
            print(f"ERROR: {e}")
        print()
        print("-" * 100)

asyncio.run(main())
