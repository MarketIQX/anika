from pathlib import Path
import re

code = Path("app/tools/gmail_tool.py").read_text(encoding="utf-8")

# Find functions that build/return the gmail service
print("=" * 70)
print("Functions in gmail_tool.py:")
print("=" * 70)
for m in re.finditer(r"^def (\w+)\(", code, re.MULTILINE):
    print(f"  def {m.group(1)}()")

print()
print("=" * 70)
print("Looking for 'service' or 'build' references:")
print("=" * 70)
for m in re.finditer(r".{40}(service|build\(|googleapiclient).{60}", code, re.IGNORECASE):
    snippet = m.group().replace("\n", " ")[:200]
    print(f"  {snippet}")
