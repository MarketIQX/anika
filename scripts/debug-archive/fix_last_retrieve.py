from pathlib import Path

p = Path("app/cognitive/library.py")
code = p.read_text(encoding="utf-8")

OLD = "WHERE is_active = 1 AND kind IN ('rule','policy') AND scope='universal'"
NEW = "WHERE is_active = 1 AND kind IN ('rule','policy') AND purpose IN ('voice_example','firm_policy','firm_fact','question_template','workflow_rule') AND scope='universal'"

if OLD in code and NEW not in code:
    code = code.replace(OLD, NEW)
    p.write_text(code, encoding="utf-8")
    print("Patched retrieve_rules else-branch")
elif NEW in code:
    print("Already patched")
else:
    print("NOT FOUND — dumping else branch:")
    import re
    m = re.search(r"else:\s*rows = fetch_all\(.*?\)", code, re.DOTALL)
    if m:
        print(m.group()[:500])

# Count purpose IN occurrences
count = code.count("purpose IN")
print(f"Total purpose IN filters: {count}")

# Verify all 5 retrieval paths now have the filter
import sys
for mod in list(sys.modules):
    if "library" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.cognitive import library
print("library module imports clean")
