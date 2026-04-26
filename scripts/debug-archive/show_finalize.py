from pathlib import Path
code = Path("app/cognitive/teaching.py").read_text(encoding="utf-8")

import re
m = re.search(r"async def finalize_queue.*?(?=\nasync def |\ndef [a-z])", code, re.DOTALL)
if m:
    print(m.group()[:2500])
