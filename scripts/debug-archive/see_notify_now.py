from pathlib import Path
import re

p = Path("app/tools/notify_tool.py")
code = p.read_text(encoding="utf-8")
print(f"File size: {len(code)} chars")
print()

# Show the full file
print("FULL CONTENT:")
print("=" * 80)
print(code)
