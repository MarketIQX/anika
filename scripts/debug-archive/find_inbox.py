from pathlib import Path
code = Path("app/dashboard/routes.py").read_text(encoding="utf-8")
import re
m = re.search(r"@router\.get\(.?/inbox.?\).*?(?=@router\.)", code, re.DOTALL)
if m:
    print(m.group()[:1200])
else:
    print("not found - searching for inbox")
    for i, line in enumerate(code.splitlines(), 1):
        if "inbox" in line.lower():
            print(f"L{i}: {line}")
