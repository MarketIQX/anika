from pathlib import Path
import re

code = Path("app/dashboard/routes.py").read_text(encoding="utf-8")

# Find the file upload block in /train/teach
m = re.search(r"for uf in files:.*?created_ids\.append\(qid\)", code, re.DOTALL)
if m:
    print("=" * 80)
    print("Current file upload flow in /train/teach:")
    print("=" * 80)
    print(m.group())
