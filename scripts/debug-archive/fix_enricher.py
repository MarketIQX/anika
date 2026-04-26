from pathlib import Path

p = Path("app/agents/enricher.py")
code = p.read_text(encoding="utf-8")

# Patch 1 — bump max_turns from 12 to 20
old1 = "max_turns=12"
new1 = "max_turns=20"
if old1 in code:
    code = code.replace(old1, new1)
    print("Bumped max_turns 12 -> 20")
else:
    print("max_turns=12 not found")

# Also update the comment
old_comment = "# Why 12: the enricher has 4 tools and the model typically calls 2-3 of\n        # them before committing to an output; 12 gives comfortable headroom."
new_comment = "# Why 20: enricher has 4 tools, expected 2-4 tool calls + final answer = ~6 turns.\n        # Bumped from 12 to 20 after observed retries hitting the limit on complex emails.\n        # Combined with stricter tool-call budget in INSTRUCTIONS below."
if old_comment in code:
    code = code.replace(old_comment, new_comment)
    print("Updated comment explaining max_turns=20")

# Patch 2 — tighten the tool-call budget language to be more directive
old_budget = """TOOL-CALL BUDGET (STRICT):
  - Use AT MOST 4 tool calls total across all tools.
  - After 4 tool calls, STOP calling tools and return your best-judgment output.
  - Missing data defaults:
      unknown service_line -> "other"
      unknown routing_partner -> "CA S V Prakasha"
      unknown urgency -> "warm"
      unknown sender -> treat as new_contact
  - Do NOT loop retrying the same tool. If a tool returns nothing, move on.
  - Incomplete is better than stuck."""

new_budget = """TOOL-CALL BUDGET (HARD LIMIT - YOU WILL BE TERMINATED IF YOU EXCEED):
  - You may call AT MOST 3 tools. Call each tool AT MOST ONCE.
  - PREFERRED ORDER:
      1. tool_lookup_client(email) - to know if existing client
      2. tool_retrieve_similar_drafts(text, service_line) - to infer service_line
      3. (optional) tool_get_routing_partner(service_line)
  - DO NOT call tool_retrieve_firm_snippets - the Drafter handles positioning.
  - DO NOT call the same tool twice with similar args.
  - DO NOT keep retrying if a tool returns empty - just MOVE ON.
  - After 3 tool calls (or fewer), you MUST return the EnricherOutput JSON. No more tool calls.

DEFAULTS (use these immediately when uncertain - DO NOT call more tools to disambiguate):
  - unknown service_line -> "other"
  - unknown routing_partner -> "CA S V Prakasha"
  - unknown urgency -> "warm"
  - unknown sender_org -> ""
  - unknown sender_country -> ""

Incomplete enrichment is FINE. Stuck enrichment is NOT."""

if old_budget in code:
    code = code.replace(old_budget, new_budget)
    print("Tightened tool-call budget instructions")
else:
    print("Old budget text not found exactly - showing what's there:")
    idx = code.find("TOOL-CALL BUDGET")
    if idx >= 0:
        print(code[idx:idx+800])

p.write_text(code, encoding="utf-8")

# Verify import
import sys
for mod in list(sys.modules):
    if "enricher" in mod or "app.agents" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.agents import enricher
    print()
    print("enricher imports cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
