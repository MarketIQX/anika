from pathlib import Path
import re

p = Path("app/agents/classifier.py")
code = p.read_text(encoding="utf-8")
print(f"File: {p} ({len(code)} chars)")
print()

# Show the output schema (categories)
print("=" * 80)
print("Classifier output schema:")
print("=" * 80)
m = re.search(r"class\s+ClassifierOutput.*?(?=\nclass|\ndef |\nINSTRUCTIONS)", code, re.DOTALL)
if m:
    print(m.group())

# Show the category Literal
print()
print("=" * 80)
print("Category Literal type:")
print("=" * 80)
m2 = re.search(r"category[^=]*=\s*Field.*?\)", code, re.DOTALL)
if m2:
    print(m2.group()[:500])

# Show INSTRUCTIONS
print()
print("=" * 80)
print("Classifier INSTRUCTIONS (first 3000 chars):")
print("=" * 80)
m3 = re.search(r"INSTRUCTIONS\s*=\s*[\"']{3}.*?[\"']{3}", code, re.DOTALL)
if m3:
    print(m3.group()[:3000])

# Find where orchestrator handles classifier output
print()
print("=" * 80)
print("Orchestrator — what happens for each category?")
print("=" * 80)
orch = Path("app/agents/orchestrator.py").read_text(encoding="utf-8")
# Show the dispatch logic
m4 = re.search(r"category\s*==\s*[\"'].*?(?=\n\n|\nasync def )", orch, re.DOTALL)
# Better: find all "category ==" comparisons
for m in re.finditer(r'category\s*[!=]+\s*[\"\']([^\"\']+)[\"\']', orch):
    print(f"  Branch: category == '{m.group(1)}'")
