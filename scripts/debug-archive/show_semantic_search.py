from pathlib import Path
import re

p = Path("app/tools/memory_tool.py")
code = p.read_text(encoding="utf-8")

# Show semantic_search + matches functions in full
for fn_name in ["semantic_search", "matches"]:
    m = re.search(rf"def {fn_name}\(.*?(?=\ndef |\Z)", code, re.DOTALL)
    if m:
        print("=" * 80)
        print(f"Function: {fn_name}")
        print("=" * 80)
        print(m.group()[:2500])
        print()
