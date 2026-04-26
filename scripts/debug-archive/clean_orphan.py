from pathlib import Path

p = Path("app/tools/knowledge_tool.py")
code = p.read_text(encoding="utf-8")

# The orphan starts at "    Falls back to a minimal default" and ends at the closing ")"
# of the return statement on line 62.
ORPHAN = '''
    Falls back to a minimal default if the firm_knowledge row is missing —
    this happens only if backfill hasn't run, and we don't want drafting to
    crash in that state.
    """
    sig = get_firm_fact("signature_block")
    if sig:
        return sig
    return (
        "Warm regards,\\n\\n"
        "S V Prakasha\\n"
        "Partner\\n"
        "Balakrishna & Co., Chartered Accountants\\n"
        "#24, 3rd Floor, 10th Cross, Wilson Garden, Bangalore 560 027\\n"
        "+91 86182 59712 | prakasha@balakrishnaandco.com\\n"
        "www.balakrishnaandco.com"
    )
'''

if ORPHAN in code:
    code = code.replace(ORPHAN, "\n")
    p.write_text(code, encoding="utf-8")
    print("Removed orphan block")
else:
    print("Orphan not found via exact match. Trying line-based removal...")
    lines = code.splitlines()
    # Lines 47-62 (1-indexed). In Python list, that's index 46-61.
    # Verify: line 47 should start with "    Falls back"
    if len(lines) > 46 and "Falls back" in lines[46]:
        # Find the end of the orphan — the last line of the bogus return tuple
        # That's the line containing "www.balakrishnaandco.com"" or `    )`
        end_idx = None
        for i in range(46, min(len(lines), 70)):
            if lines[i].strip() == ")":
                end_idx = i
                break
        if end_idx:
            print(f"Removing lines 47 through {end_idx + 1}")
            del lines[46:end_idx + 1]
            code = "\n".join(lines)
            p.write_text(code, encoding="utf-8")
            print("Removed via line-based approach")
        else:
            print("Could not find orphan end — manual cleanup needed")
    else:
        print("Line 47 does not contain 'Falls back' — orphan may already be gone")

# Verify imports
import sys
for mod in list(sys.modules):
    if "knowledge_tool" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.tools import knowledge_tool
    print()
    print("knowledge_tool imports cleanly")
    sig = knowledge_tool.get_signature_block()
    print()
    print("get_signature_block() returns:")
    print(sig)
except Exception as e:
    print(f"\nIMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()

# Show the cleaned file region
print()
print("=" * 70)
print("Lines 30-50 after cleanup:")
print("=" * 70)
fresh = Path("app/tools/knowledge_tool.py").read_text(encoding="utf-8")
for i, line in enumerate(fresh.splitlines()[29:50], start=30):
    print(f"{i:3d}| {line}")
