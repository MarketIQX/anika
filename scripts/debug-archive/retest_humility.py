import asyncio
from app.agents.humility_layer import articulate_uncertainty

content = """Partnership Deed
This deed of partnership is made this 15th day of April 2026 between Sri A B Rao, son of Late Sri X Y Rao (hereinafter called the First Partner) and Sri C D Kumar, son of Late Sri M N Kumar (hereinafter called the Second Partner).

The partners hereby agree to carry on the business of manufacturing and trading in industrial goods under the firm name 'Rao Kumar Industries' with profit sharing ratio of 60:40."""

async def main():
    result = await articulate_uncertainty(content=content)
    print("=" * 90)
    print("RE-TEST — Partnership deed (previously hallucinated 'legal_document')")
    print("=" * 90)
    print()
    print("NOTICED FEATURES:")
    for f in result.noticed_features:
        print(f"  * {f}")
    print()
    print(f"BEST GUESS: {result.best_guess_purpose} (conf: {result.best_guess_confidence:.2f})")
    print(f"ALTERNATIVES: {result.alternative_purposes}")
    print()
    print(f"SUGGESTED CUSTOM LABEL: {result.suggested_custom_label}")
    print()
    print(f"UNCERTAINTY: {result.uncertainty_source}")
    print()
    print(f"QUESTION: {result.single_focused_question}")

    # Validation
    valid = ["voice_example", "classifier_example", "document_type", "question_template", "workflow_rule", "firm_fact", "firm_policy", "reference_material"]
    print()
    print("=" * 90)
    if result.best_guess_purpose in valid:
        print(f"PASS — best_guess_purpose is a valid literal: {result.best_guess_purpose}")
    else:
        print(f"FAIL — best_guess_purpose is NOT valid: {result.best_guess_purpose}")
    if result.suggested_custom_label:
        print(f"BONUS — custom label suggested: {result.suggested_custom_label}")

asyncio.run(main())
