from pathlib import Path
import re

p = Path("app/agents/drafter.py")
code = p.read_text(encoding="utf-8")

# Update assemble_prompt signature to return cognitive_state too
OLD = '''def assemble_prompt(
    *,
    service_line: str | None,
    enquiry_body: str,
) -> tuple[str, list[int]]:
    """Build the Drafter prompt at runtime. Returns (prompt_text, used_library_ids).

    used_library_ids lists every knowledge_library row that went into the
    prompt, so the orchestrator can bump applied_count after the draft lands.
    """
    rules = library.retrieve_rules(service_line)
    facts = library.retrieve_facts(service_line)
    # Semantic retrieval for examples — keyed by the actual enquiry body.
    examples = library.retrieve_examples(
        query_text=enquiry_body[:2000],
        service_line=service_line,
        top_k=5,
    )

    sections = [
        DRAFTER_HEADER,
        _format_rules(rules),
        _format_examples(examples),
        _format_facts(facts),
        SIGNATURE_INSTRUCTION,
        OUTPUT_SCHEMA_HINT,
    ]
    prompt = "\\n\\n".join(s for s in sections if s)

    ids = [r["id"] for r in rules] + [r["id"] for r in examples] + [r["id"] for r in facts]
    return prompt, ids'''

NEW = '''def assemble_prompt(
    *,
    service_line: str | None,
    enquiry_body: str,
) -> tuple[str, list[int], dict]:
    """Build the Drafter prompt at runtime.

    Returns (prompt_text, used_library_ids, cognitive_state_info).

    cognitive_state_info comes from library.voice_coverage() — tells the
    orchestrator whether this draft was cold_start / learning / learned,
    so that info can be stored on the draft and surfaced to the user.

    If cognitive state is cold_start, the prompt includes an honesty banner
    instructing the Drafter to write conservatively and NOT fabricate credentials.
    """
    rules = library.retrieve_rules(service_line)
    facts = library.retrieve_facts(service_line)

    # Cognitive state — how much learned voice do we have?
    coverage = library.voice_coverage(service_line)
    state = coverage["cognitive_state"]

    # Semantic retrieval for examples — ONLY when state is 'learning' or 'learned'.
    # For cold_start, we deliberately skip voice_examples to avoid pulling cross-service noise.
    if state == "cold_start":
        examples = []
    else:
        examples = library.retrieve_examples(
            query_text=enquiry_body[:2000],
            service_line=service_line,
            top_k=5,
        )

    # Build an honesty banner based on cognitive state
    if state == "cold_start":
        honesty = (
            "IMPORTANT — COGNITIVE STATE: COLD START\\n"
            f"You have NO verified voice examples for service_line '{service_line or \"universal\"}'.\\n"
            "This means you have not yet learned how CA Prakasha writes first replies for this area.\\n"
            "\\n"
            "In this mode you MUST:\\n"
            "  - Write a CONSERVATIVE, NEUTRAL first reply\\n"
            "  - Do NOT quote firm credentials (no '150 foreign companies', no '37 years experience', no client counts)\\n"
            "  - Do NOT use marketing positioning language\\n"
            "  - Acknowledge the enquiry politely\\n"
            "  - Ask focused clarifying questions relevant to the service_line\\n"
            "  - Offer a short scoping call to understand requirements\\n"
            "  - Keep tone professional, not promotional\\n"
            "\\n"
            "After the user edits and approves this draft, your edit will become\\n"
            "the first voice_example for this service_line. Future drafts will learn from it."
        )
    elif state == "learning":
        honesty = (
            "COGNITIVE STATE: LEARNING\\n"
            f"You have {coverage['count']} voice example(s) for service_line '{service_line or \"universal\"}'.\\n"
            "Still early in learning. Mirror the voice examples provided below closely.\\n"
            "Remain conservative on credentials — use only what the examples use."
        )
    else:
        honesty = None  # learned — no banner needed

    sections = [
        DRAFTER_HEADER,
        honesty,
        _format_rules(rules),
        _format_examples(examples),
        _format_facts(facts),
        SIGNATURE_INSTRUCTION,
        OUTPUT_SCHEMA_HINT,
    ]
    prompt = "\\n\\n".join(s for s in sections if s)

    ids = [r["id"] for r in rules] + [r["id"] for r in examples] + [r["id"] for r in facts]
    return prompt, ids, coverage'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Updated drafter.assemble_prompt() with cognitive state awareness")
else:
    print("OLD block not found — assemble_prompt() signature may differ")
    # Fallback: find and print current version
    m = re.search(r"def assemble_prompt.*?(?=\ndef )", code, re.DOTALL)
    if m:
        print("Current version:")
        print(m.group()[:1500])
