from pathlib import Path
import re

p = Path("app/agents/enricher.py")
code = p.read_text(encoding="utf-8")

print(f"File size: {len(code)} chars")
print()

# Show the enrich() function — the one hitting max_turns
m = re.search(r"async def enrich\(.*?(?=\nasync def |\ndef [a-z]|\Z)", code, re.DOTALL)
if m:
    print("=" * 80)
    print("enrich() function:")
    print("=" * 80)
    print(m.group()[:2500])

# Show INSTRUCTIONS or system prompt for the agent
print()
print("=" * 80)
print("Agent build / instructions:")
print("=" * 80)
m2 = re.search(r"INSTRUCTIONS\s*=\s*[\"']{3}.*?[\"']{3}", code, re.DOTALL)
if m2:
    print(m2.group()[:3000])

# Show tools the enricher has access to
print()
print("=" * 80)
print("Tools the agent uses:")
print("=" * 80)
m3 = re.search(r"tools\s*=\s*\[.*?\]", code, re.DOTALL)
if m3:
    print(m3.group())

# What's max_turns set to?
print()
m4 = re.search(r"max_turns\s*=\s*(\d+)", code)
if m4:
    print(f"max_turns currently set to: {m4.group(1)}")
