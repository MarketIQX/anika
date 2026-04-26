from pathlib import Path
code = Path("app/dashboard/routes.py").read_text(encoding="utf-8")

# Check imports
import re
imports = re.findall(r"^from app\.db import .*$", code, re.MULTILINE)
print("app.db imports:")
for imp in imports:
    print(f"  {imp}")

# Check what _classify_and_persist uses
print()
print("=== _classify_and_persist function body ===")
m = re.search(r"async def _classify_and_persist.*?(?=\n    content = )", code, re.DOTALL)
if m:
    print(m.group()[:2000])
