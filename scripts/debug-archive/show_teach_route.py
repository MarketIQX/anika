from pathlib import Path
code = Path("app/dashboard/routes.py").read_text(encoding="utf-8")

import re
# Find the /train/teach route
m = re.search(r'@router\.post\(["\']\/train\/teach["\'].*?(?=@router\.)', code, re.DOTALL)
if m:
    print("=" * 80)
    print("CURRENT /train/teach ROUTE")
    print("=" * 80)
    print(m.group())
else:
    print("Route not found - searching for alternative pattern")
    for i, line in enumerate(code.splitlines(), 1):
        if "train/teach" in line.lower() or "train_teach" in line.lower():
            print(f"L{i}: {line}")
