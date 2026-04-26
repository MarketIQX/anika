from pathlib import Path
p = Path("app/cognitive/learning_engine.py")
if p.exists():
    code = p.read_text(encoding="utf-8")
    print(f"File size: {len(code)} chars")
    print("=" * 80)
    print(code[:4000])
else:
    print("File does not exist")

# Also — the approver.approve function (what happens on approve)
print()
print("=" * 80)
print("approver.approve — what happens on approve")
print("=" * 80)
p2 = Path("app/agents/approver.py")
code2 = p2.read_text(encoding="utf-8")
import re
m = re.search(r"async def approve\(.*?(?=\nasync def |\ndef |\Z)", code2, re.DOTALL)
if m:
    print(m.group()[:2500])
