from pathlib import Path
import os, re

# Find all callers of get_signature_block
print("=" * 80)
print("Who CALLS knowledge_tool.get_signature_block()?")
print("=" * 80)

for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = Path(root) / f
        content = fp.read_text(encoding="utf-8")
        if "get_signature_block" in content:
            for m in re.finditer(r".{80}get_signature_block.{50}", content, re.DOTALL):
                print(f"\n{fp}:")
                print(f"  {m.group()[:250]}")
