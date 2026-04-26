from pathlib import Path
import os, re

# Search for places that READ signature_block from firm_knowledge specifically
print("=" * 80)
print("Who reads firm_knowledge.signature_block specifically?")
print("=" * 80)

for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if not f.endswith(".py"):
            continue
        fp = Path(root) / f
        content = fp.read_text(encoding="utf-8")
        if "signature_block" in content.lower():
            print(f"\n=== {fp} ===")
            for m in re.finditer(r".{50}signature_block.{100}", content, re.IGNORECASE | re.DOTALL):
                print(f"  {m.group()[:200]}")

# The Drafter's actual flow — what does ensure_signature read?
print()
print("=" * 80)
print("ensure_signature() in firm_identity.py — its source of truth")
print("=" * 80)
fi = Path("app/config/firm_identity.py").read_text(encoding="utf-8")
print(fi[:2000])
