from pathlib import Path
import re

code = Path("app/agents/enricher.py").read_text(encoding="utf-8")

# Verify the logger import is present
print("Checking enricher.py current state:")
print(f"  'import logging' present:    {'import logging' in code}")
print(f"  'logger = logging.' present: {'logger = logging.getLogger' in code}")
print(f"  Tool-less refactor landed:   {'tools=[' not in code or '#tools=[' in code}")

# Check the agent build specifically
print()
m = re.search(r'agent\s*=\s*Agent\([^)]+\)', code, re.DOTALL)
if m:
    block = m.group()
    has_tools = 'tools=' in block
    print(f"  Agent() has tools=[]:        {has_tools}")
    if has_tools:
        print(f"    block: {block[:300]}")
