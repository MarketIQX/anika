from pathlib import Path
import re

p = Path("app/agents/drafter.py")
code = p.read_text(encoding="utf-8")

# Replace the broken honesty block with a cleaner version using .format() instead of f-string
# Find the line that broke and the whole honesty block

OLD_BLOCK = '''    # Build an honesty banner based on cognitive state
    if state == "cold_start":
        honesty = (
            "IMPORTANT — COGNITIVE STATE: COLD START\\n"
            f"You have NO verified voice examples for service_line '{service_line or "universal"}'.\\n"
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
            f"You have {coverage['count']} voice example(s) for service_line '{service_line or "universal"}'.\\n"
            "Still early in learning. Mirror the voice examples provided below closely.\\n"
            "Remain conservative on credentials — use only what the examples use."
        )
    else:
        honesty = None  # learned — no banner needed'''

NEW_BLOCK = '''    # Build an honesty banner based on cognitive state
    sl_display = service_line if service_line else "universal"
    if state == "cold_start":
        honesty = (
            "IMPORTANT - COGNITIVE STATE: COLD START\\n"
            "You have NO verified voice examples for service_line '" + sl_display + "'.\\n"
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
            "You have " + str(coverage["count"]) + " voice example(s) for service_line '" + sl_display + "'.\\n"
            "Still early in learning. Mirror the voice examples provided below closely.\\n"
            "Remain conservative on credentials - use only what the examples use."
        )
    else:
        honesty = None  # learned - no banner needed'''

if OLD_BLOCK in code:
    code = code.replace(OLD_BLOCK, NEW_BLOCK)
    p.write_text(code, encoding="utf-8")
    print("Fixed honesty block f-string escaping")
else:
    print("OLD block not found; trying loose match")
    # Find the broken f-string line
    idx = code.find('service_line or "universal"')
    if idx >= 0:
        print(f"Found problematic line at position {idx}")
        # Show surrounding 300 chars
        print(code[max(0,idx-100):idx+200])

# Verify imports
import sys
for mod in list(sys.modules):
    if "drafter" in mod or "app.agents" in mod or "app.cognitive" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.agents import drafter
    print()
    print("drafter imports cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
