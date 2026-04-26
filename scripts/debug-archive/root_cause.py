from pathlib import Path
import re

# Check the agent build — how is structured output enforced?
p = Path("app/agents/enricher.py")
code = p.read_text(encoding="utf-8")

print("=" * 80)
print("Enricher agent build — output_type setting")
print("=" * 80)
m = re.search(r"def _build_agent\(.*?\):.*?(?=\ndef |\Z)", code, re.DOTALL)
if m:
    print(m.group())
print()

# Compare to classifier — same SDK, no tools, works fine
print("=" * 80)
print("Classifier agent build — for comparison")
print("=" * 80)
c = Path("app/agents/classifier.py").read_text(encoding="utf-8")
m2 = re.search(r"def _build_agent\(.*?\):.*?(?=\ndef |\Z)", c, re.DOTALL)
if m2:
    print(m2.group())

# How does Enricher pass tools? Tool definitions
print()
print("=" * 80)
print("Enricher tool list + tool_choice setting")
print("=" * 80)
# Look for Agent() constructor call in enricher
m3 = re.search(r"Agent\([^)]*\)", code, re.DOTALL)
if m3:
    print(m3.group())

# Check if tool_choice is set
if "tool_choice" in code:
    print()
    print("tool_choice IS set somewhere")
    for m in re.finditer(r"tool_choice[^,\n]*", code):
        print(f"  {m.group()}")
else:
    print()
    print("tool_choice is NOT set — model decides freely whether to call tools")
