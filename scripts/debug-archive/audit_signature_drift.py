from pathlib import Path
import os, re

# Find anything that reads firm_knowledge.signature_block
print("=" * 70)
print("Who reads firm_knowledge?")
print("=" * 70)

queries = []
for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = Path(root) / f
        content = fp.read_text(encoding="utf-8")
        if "firm_knowledge" in content.lower():
            for m in re.finditer(r"firm_knowledge[^\n]{0,200}", content, re.IGNORECASE):
                queries.append((str(fp), m.group()))

for fp, q in queries[:20]:
    print(f"\n{fp}:")
    print(f"  {q[:200]}")

# Also check the backfill_memory FIRM_FACTS list — show what it seeds for signature
print()
print("=" * 70)
print("FIRM_FACTS in backfill_memory.py — search for signature entry")
print("=" * 70)
bf = Path("app/jobs/backfill_memory.py").read_text(encoding="utf-8")
m = re.search(r'\("signature_block",.*?\),', bf, re.DOTALL)
if m:
    print("Found signature_block FIRM_FACTS entry:")
    print(m.group())
