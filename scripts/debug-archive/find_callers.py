from pathlib import Path
import re

# Find all call sites of assemble_prompt
print("=" * 80)
print("Finding callers of assemble_prompt()")
print("=" * 80)

# Search all Python files
import os
matches = []
for root, dirs, files in os.walk("app"):
    # Skip __pycache__
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = Path(root) / f
        content = fp.read_text(encoding="utf-8")
        if "assemble_prompt(" in content:
            # Show each occurrence with context
            for m in re.finditer(r"assemble_prompt\([^)]*\)", content):
                start = max(0, m.start() - 100)
                end = min(len(content), m.end() + 200)
                matches.append((str(fp), m.start(), content[start:end]))

for fp, pos, ctx in matches:
    print()
    print(f"FILE: {fp}")
    print("-" * 80)
    print(ctx)
    print()
