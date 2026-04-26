from pathlib import Path
import re

# Find the actual signature of orchestrator.handle and what it expects
p = Path("app/agents/orchestrator.py")
code = p.read_text(encoding="utf-8")

# Show handle() signature
m = re.search(r"async def handle\(.*?\n.*?:.*?(?=\n    [a-z]|\n    #)", code, re.DOTALL)
if m:
    print("handle() signature:")
    print(m.group()[:500])
print()

# Find the imported message type
m2 = re.search(r"from .+? import .*Message.*", code)
if m2:
    print("Message import:")
    print(m2.group())

# Search for the dataclass definition
print()
print("Looking for FetchedMessage / IncomingMessage classes:")
for fname in ["app/tools/gmail_tool.py", "app/agents/orchestrator.py"]:
    pp = Path(fname)
    if pp.exists():
        c = pp.read_text(encoding="utf-8")
        for cm in re.finditer(r"@dataclass[^@]*class (\w+)", c, re.DOTALL):
            print(f"  {fname}: class {cm.group(1)}")

# Also look at how poll_gmail constructs the msg
print()
print("How poll_gmail constructs msg:")
p2 = Path("app/jobs/poll_gmail.py")
c2 = p2.read_text(encoding="utf-8")
m3 = re.search(r"msg = gmail_tool\.fetch_message.*?orchestrator\.handle\(msg\)", c2, re.DOTALL)
if m3:
    print(m3.group())
