from pathlib import Path
import re

# Find Category Literal in schemas
schemas = Path("app/agents/schemas.py").read_text(encoding="utf-8")
m = re.search(r"^Category\s*=.*?(?=\n\n)", schemas, re.MULTILINE | re.DOTALL)
if m:
    print("Category Literal:")
    print(m.group())
print()

# Show full handle() to see the new_enquiry vs other branches
orch = Path("app/agents/orchestrator.py").read_text(encoding="utf-8")
print("=" * 70)
print("Orchestrator handle() — categories branching (full):")
print("=" * 70)
m2 = re.search(r"category: Category = cls\.category.*?(?=\nasync def |\ndef [a-z]|\Z)", orch, re.DOTALL)
if m2:
    print(m2.group()[:3000])
