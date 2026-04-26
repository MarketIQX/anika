from pathlib import Path
import re

p = Path("app/tools/memory_tool.py")
code = p.read_text(encoding="utf-8")

print("Current memory_tool.py — looking for retrieval functions:")
print("-" * 80)

# Find all FROM memory queries
matches = list(re.finditer(r"FROM memory\b[^)]*?(?=\"\"\"|'''|\)|\n\s*$)", code, re.DOTALL | re.IGNORECASE))
for i, m in enumerate(matches, 1):
    start = max(0, m.start() - 200)
    end = min(len(code), m.end() + 100)
    print(f"--- Match {i} at position {m.start()} ---")
    print(code[start:end])
    print()

# Also show function defs that touch memory
print()
print("Functions in memory_tool.py:")
for m in re.finditer(r"(async )?def (\w+)\(", code):
    print(f"  {m.group()}")
