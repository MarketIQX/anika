from pathlib import Path

# ============================================================
# Patch 1 — Enricher: catch MaxTurnsExceeded with safe fallback
# ============================================================
p = Path("app/agents/enricher.py")
code = p.read_text(encoding="utf-8")

OLD = '''        # Why 20: enricher has 4 tools, expected 2-4 tool calls + final answer = ~6 turns.
        # Bumped from 12 to 20 after observed retries hitting the limit on complex emails.
        # Combined with stricter tool-call budget in INSTRUCTIONS below.
        result = await Runner.run(agent, input=user_input, max_turns=20)
        output: EnricherOutput = result.final_output  # type: ignore[assignment]
        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning'''

NEW = '''        # Why 20: enricher has 4 tools, expected 2-4 tool calls + final answer = ~6 turns.
        # Bumped from 12 to 20. If model still loops past that, fall back to safe
        # defaults (Anthropic-style graceful degradation). Pipeline continues with
        # an honest "I struggled to enrich" flag so the partner can see it.
        try:
            result = await Runner.run(agent, input=user_input, max_turns=20)
            output: EnricherOutput = result.final_output  # type: ignore[assignment]
        except Exception as exc:
            from agents.exceptions import MaxTurnsExceeded
            if not isinstance(exc, MaxTurnsExceeded):
                raise
            logger.warning(
                "Enricher exhausted max_turns on email %s - falling back to heuristic defaults",
                email_id,
            )
            # Heuristic service_line from keywords (best-effort, no LLM)
            text_lower = ((subject or "") + " " + (body_plain or "")).lower()
            heuristic_sl = "other"
            for keyword, sl in [
                ("nri", "nri_tax"),
                ("foreign asset", "nri_tax"),
                ("schedule fa", "nri_tax"),
                ("nro account", "nri_tax"),
                ("nre account", "nri_tax"),
                ("subsidiary", "foreign_subsidiary"),
                ("incorporation", "foreign_subsidiary"),
                ("wos", "foreign_subsidiary"),
                ("transfer pric", "transfer_pricing"),
                ("3ceb", "transfer_pricing"),
                ("gst", "gst_indirect"),
                ("indirect tax", "gst_indirect"),
                ("audit", "audit"),
                ("roc", "secretarial_roc"),
                ("compliance", "secretarial_roc"),
                ("secretarial", "secretarial_roc"),
                ("cfo", "virtual_cfo"),
                ("startup", "virtual_cfo"),
            ]:
                if keyword in text_lower:
                    heuristic_sl = sl
                    break

            output = EnricherOutput(
                sender_name=from_name or "",
                sender_org="",
                sender_country="",
                likely_service_line=heuristic_sl,
                urgency="warm",
                routing_partner="CA S V Prakasha",
                summary=(
                    f"{from_name or from_email} sent an enquiry. "
                    f"Anika could not fully enrich this email - please read the original carefully."
                ),
                reasoning=(
                    "ENRICHMENT FALLBACK: Enricher exceeded max_turns budget on this email. "
                    "Service line inferred via keyword heuristic; sender details left blank. "
                    "Partner should review the original email closely before approving."
                ),
            )

        ctx["output"] = output.model_dump()
        ctx["reasoning"] = output.reasoning'''

if OLD in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Patched enricher.py - MaxTurnsExceeded fallback added")
else:
    print("OLD enricher block not found - dumping current state")
    idx = code.find("max_turns=20")
    if idx >= 0:
        print(code[max(0,idx-200):idx+400])

# ============================================================
# Patch 2 — Drafter: detect fallback enrichment, add partner banner
# ============================================================
p2 = Path("app/agents/drafter.py")
code2 = p2.read_text(encoding="utf-8")

# We'll modify assemble_prompt to include an extra honesty section when
# enrichment looks like it came from fallback (reasoning contains "FALLBACK")
# Pass enrichment in via a new param, OR detect at draft_reply level.
# Simpler: detect at draft_reply level and prepend a body-level banner.

# Find draft_reply function and inject the fallback detection
OLD2 = '''    service_line = enrichment.likely_service_line
    prompt, used_ids, coverage = assemble_prompt(service_line=service_line, enquiry_body=body_plain)'''

NEW2 = '''    service_line = enrichment.likely_service_line

    # Detect enrichment fallback (Enricher exceeded max_turns and we used heuristics)
    enrichment_was_fallback = (
        "FALLBACK" in (enrichment.reasoning or "").upper()
        or "could not fully enrich" in (enrichment.summary or "").lower()
    )

    prompt, used_ids, coverage = assemble_prompt(service_line=service_line, enquiry_body=body_plain)

    # If enrichment fell back, add an honest note to the prompt so the Drafter
    # knows it is working with partial intelligence.
    if enrichment_was_fallback:
        prompt = prompt + (
            "\\n\\nIMPORTANT - PARTIAL ENRICHMENT:\\n"
            "The Enricher could not fully analyse this enquiry (it timed out on tool calls).\\n"
            "Service line was guessed via keyword heuristic. Sender details may be incomplete.\\n"
            "Draft conservatively. Ask focused clarifying questions. Do not make assumptions\\n"
            "about the sender or their specific needs - the partner will read the original email.\\n"
        )'''

if OLD2 in code2:
    code2 = code2.replace(OLD2, NEW2)
    p2.write_text(code2, encoding="utf-8")
    print("Patched drafter.py - fallback-aware prompt assembly")
else:
    print("OLD2 drafter block not found")

# ============================================================
# Verify imports
# ============================================================
import sys
for mod in list(sys.modules):
    if "enricher" in mod or "drafter" in mod or "app.agents" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.agents import enricher, drafter
    print()
    print("Both modules import cleanly")
    # Function counts
    e_code = Path("app/agents/enricher.py").read_text(encoding="utf-8")
    d_code = Path("app/agents/drafter.py").read_text(encoding="utf-8")
    print(f"enricher.py: {e_code.count(chr(10) + 'async def ') + e_code.count(chr(10) + 'def ')} def lines, {len(e_code)} chars")
    print(f"drafter.py:  {d_code.count(chr(10) + 'async def ') + d_code.count(chr(10) + 'def ')} def lines, {len(d_code)} chars")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
