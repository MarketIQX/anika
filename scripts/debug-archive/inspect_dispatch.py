from pathlib import Path
import re

# Find where ClassifierOutput is defined (probably a schema file)
print("Searching for ClassifierOutput definition:")
import os
for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = Path(root) / f
        content = fp.read_text(encoding="utf-8")
        if "class ClassifierOutput" in content:
            print(f"\n=== {fp} ===")
            m = re.search(r"class ClassifierOutput.*?(?=\nclass |\Z)", content, re.DOTALL)
            if m:
                print(m.group()[:1500])

# Show orchestrator dispatch logic
print()
print("=" * 80)
print("Orchestrator dispatch — full handle() function")
print("=" * 80)
orch = Path("app/agents/orchestrator.py").read_text(encoding="utf-8")
m = re.search(r"async def handle\(.*?(?=\nasync def |\ndef [a-z]|\Z)", orch, re.DOTALL)
if m:
    print(m.group()[:3500])
