from pathlib import Path

p = Path("app/tools/notify_tool.py")
code = p.read_text(encoding="utf-8")
print(f"File: {p} ({len(code)} chars)")
print()
print("=" * 80)
print("FULL FILE CONTENTS")
print("=" * 80)
print(code)
