from pathlib import Path
p = Path("app/tools/knowledge_tool.py")
code = p.read_text(encoding="utf-8")

# Show lines 30-80 to see the damage
print(f"File size: {len(code)} chars")
print()
for i, line in enumerate(code.splitlines()[30:80], start=31):
    print(f"{i:3d}| {line}")
