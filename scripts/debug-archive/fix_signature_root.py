from pathlib import Path
import re

# ============================================================
# Fix 1 — knowledge_tool.get_signature_block() returns canonical
# ============================================================
p = Path("app/tools/knowledge_tool.py")
code = p.read_text(encoding="utf-8")

# Find the existing function and replace its body
m = re.search(
    r'def get_signature_block\(\) -> str:.*?(?=\n\n|\ndef |\Z)',
    code,
    re.DOTALL
)
if m:
    new_fn = '''def get_signature_block() -> str:
    """Return Prakash sir's signature block — the locked canonical sign-off.

    Source of truth: app/config/firm_identity.SIGNATURE_BLOCK (locked in code).
    Previously this read from firm_knowledge.signature_block which created a
    second source of truth that drifted from the locked version. That bug
    caused double-signature stacking on drafts.

    The legacy DB row in firm_knowledge.signature_block is now ignored.
    """
    from app.config.firm_identity import SIGNATURE_BLOCK
    return SIGNATURE_BLOCK'''
    code = code[:m.start()] + new_fn + code[m.end():]
    p.write_text(code, encoding="utf-8")
    print(f"Patched knowledge_tool.get_signature_block() — now returns canonical")
else:
    print("get_signature_block function not found in expected pattern")

# ============================================================
# Fix 2 — Remove signature_block from backfill_memory FIRM_FACTS
# ============================================================
p2 = Path("app/jobs/backfill_memory.py")
code2 = p2.read_text(encoding="utf-8")

# Match the multi-line tuple entry
old_seed = re.search(
    r'    \("signature_block",\s*"Warm regards.*?"signature"\),\n',
    code2,
    re.DOTALL
)
if old_seed:
    # Replace with a comment explaining why it's gone
    new_comment = '    # signature_block is NOT seeded here — it lives in app/config/firm_identity.py\n    # as a locked code constant. See knowledge_tool.get_signature_block().\n'
    code2 = code2[:old_seed.start()] + new_comment + code2[old_seed.end():]
    p2.write_text(code2, encoding="utf-8")
    print("Removed signature_block from backfill_memory.py FIRM_FACTS seed")
else:
    print("signature_block seed entry not found in expected pattern")

# ============================================================
# Verify imports
# ============================================================
import sys
for mod in list(sys.modules):
    if "knowledge_tool" in mod or "backfill_memory" in mod or "app.tools" in mod or "app.jobs" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.tools import knowledge_tool
    from app.jobs import backfill_memory
    print()
    print("Both modules import cleanly")

    # Verify the function returns the canonical
    sig = knowledge_tool.get_signature_block()
    print()
    print("get_signature_block() now returns:")
    print(sig)
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
