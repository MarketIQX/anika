import asyncio
from app.agents.humility_layer import articulate_uncertainty

test_cases = [
    {
        "name": "Ambiguous tax rule — could be domain knowledge, firm policy, or workflow",
        "content": "Section 54 exemption: Capital gains reinvested in new residential property within 2 years are exempt from tax. The property must be in India.",
    },
    {
        "name": "Partnership deed excerpt — unfamiliar document type",
        "content": """Partnership Deed
This deed of partnership is made this 15th day of April 2026 between Sri A B Rao, son of Late Sri X Y Rao (hereinafter called the First Partner) and Sri C D Kumar, son of Late Sri M N Kumar (hereinafter called the Second Partner).

The partners hereby agree to carry on the business of manufacturing and trading in industrial goods under the firm name 'Rao Kumar Industries' with profit sharing ratio of 60:40.""",
    },
    {
        "name": "ICAI ethical guideline — firm policy OR domain knowledge?",
        "content": "A Chartered Accountant should not accept engagement where his independence is likely to be compromised. Engagements involving immediate family members are prohibited under ICAI Code of Ethics Section 290.",
    },
]

async def main():
    for i, case in enumerate(test_cases, 1):
        print("=" * 100)
        print(f"TEST {i} — {case['name']}")
        print("=" * 100)
        print(f"Content preview: {case['content'][:120]}...")
        print()
        try:
            result = await articulate_uncertainty(content=case["content"])
            print("NOTICED FEATURES:")
            for f in result.noticed_features:
                print(f"  • {f}")
            print()
            print(f"BEST GUESS: {result.best_guess_purpose} (confidence: {result.best_guess_confidence:.2f})")
            print(f"ALTERNATIVES: {', '.join(result.alternative_purposes)}")
            print()
            print(f"UNCERTAINTY SOURCE:")
            print(f"  {result.uncertainty_source}")
            print()
            print(f"QUESTION FOR PRAKASH SIR:")
            print(f"  {result.single_focused_question}")
            if result.suggested_custom_label:
                print()
                print(f"SUGGESTED CUSTOM LABEL: {result.suggested_custom_label}")
        except Exception as e:
            print(f"ERROR: {e}")
        print()

asyncio.run(main())
