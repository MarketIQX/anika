from pathlib import Path
import re

code = Path("app/cognitive/library.py").read_text(encoding="utf-8")

# Find retrieve_rules, retrieve_examples, retrieve_facts
for fn in ["retrieve_rules", "retrieve_examples", "retrieve_facts"]:
    m = re.search(rf"def {fn}\(.*?(?=\ndef |\Z)", code, re.DOTALL)
    if m:
        print("=" * 80)
        print(f"FUNCTION: {fn}")
        print("=" * 80)
        print(m.group()[:800])
        print()
