from pathlib import Path

p = Path("app/cognitive/library.py")
code = p.read_text(encoding="utf-8")

# The purposes that should be auto-retrieved by Drafter
DRAFTABLE = "('voice_example','firm_policy','firm_fact','question_template','workflow_rule')"

replacements = [
    # retrieve_rules — with service_line
    (
        "WHERE is_active = 1\n               AND kind IN ('rule','policy')\n               AND (scope = 'universal' OR service_line = ?)",
        f"WHERE is_active = 1\n               AND kind IN ('rule','policy')\n               AND purpose IN {DRAFTABLE}\n               AND (scope = 'universal' OR service_line = ?)",
    ),
    # retrieve_rules — no service_line path (universal only)
    (
        "WHERE is_active = 1\n               AND kind IN ('rule','policy')\n               AND scope = 'universal'",
        f"WHERE is_active = 1\n               AND kind IN ('rule','policy')\n               AND purpose IN {DRAFTABLE}\n               AND scope = 'universal'",
    ),
    # retrieve_facts — with service_line
    (
        "WHERE is_active = 1 AND kind = 'fact'\n               AND (scope = 'universal' OR service_line = ?)",
        f"WHERE is_active = 1 AND kind = 'fact'\n               AND purpose IN {DRAFTABLE}\n               AND (scope = 'universal' OR service_line = ?)",
    ),
    # retrieve_facts — no service_line (universal only)
    (
        "WHERE is_active = 1 AND kind = 'fact' AND scope = 'universal'",
        f"WHERE is_active = 1 AND kind = 'fact' AND purpose IN {DRAFTABLE} AND scope = 'universal'",
    ),
]

changes = 0
for old, new in replacements:
    if old in code:
        code = code.replace(old, new)
        changes += 1
        print(f"Patched: {old[:60]}...")
    else:
        print(f"NOT FOUND: {old[:60]}...")

# For retrieve_examples — the SQL is templated differently (uses embeddings)
# Let me find it and add the purpose filter
import re
m = re.search(r"(SELECT v\.library_id AS id, v\.distance AS distance,.*?FROM knowledge_library_vec v.*?WHERE.*?)(\))", code, re.DOTALL)
if m:
    examples_sql_section = m.group(1)
    # Check if purpose filter already present
    if "purpose IN" not in examples_sql_section:
        # Look for "AND k.kind = 'example'" as our injection point
        if "k.kind = 'example'" in code:
            code = code.replace(
                "k.kind = 'example'",
                f"k.kind = 'example' AND k.purpose IN {DRAFTABLE}",
            )
            changes += 1
            print("Patched retrieve_examples (added purpose filter)")
        elif "kind = 'example'" in code and "AND purpose IN" not in code:
            # Simpler match
            print("retrieve_examples — trying alternative match")

p.write_text(code, encoding="utf-8")
print(f"\nTotal replacements: {changes}")

# Verify by searching for the filter
if f"purpose IN {DRAFTABLE}" in code:
    count = code.count(f"purpose IN {DRAFTABLE}")
    print(f"Purpose filter now appears {count} times in library.py")

# Import check
import sys
for mod in list(sys.modules):
    if "library" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.cognitive import library
    print("\nlibrary module imports clean")
except Exception as e:
    print(f"\nIMPORT ERROR: {e}")
