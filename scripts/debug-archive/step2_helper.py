from pathlib import Path

p = Path("app/cognitive/library.py")
code = p.read_text(encoding="utf-8")

if "def voice_coverage" in code:
    print("voice_coverage already exists — skipping")
else:
    # Append at end of file
    new_fn = '''


# --------------------------------------------------------------------------
# Cognitive state helpers (Phase 1B+)
# --------------------------------------------------------------------------

def voice_coverage(service_line: str | None) -> dict[str, Any]:
    """How much learned voice does Anika have for this service_line?

    Returns dict with:
      - count: number of voice_example entries
      - cognitive_state: 'cold_start' (0), 'learning' (1-2), 'learned' (3+)
      - service_line: the queried service_line
      - has_universal: whether universal-scope voice_examples exist as fallback
    """
    if service_line:
        sl_rows = fetch_all("""
            SELECT COUNT(*) n FROM knowledge_library
             WHERE is_active = 1
               AND purpose = 'voice_example'
               AND service_line = ?
        """, (service_line,))
    else:
        sl_rows = fetch_all("""
            SELECT COUNT(*) n FROM knowledge_library
             WHERE is_active = 1
               AND purpose = 'voice_example'
               AND (service_line IS NULL OR scope = 'universal')
        """)

    sl_count = sl_rows[0]["n"] if sl_rows else 0

    universal_rows = fetch_all("""
        SELECT COUNT(*) n FROM knowledge_library
         WHERE is_active = 1
           AND purpose = 'voice_example'
           AND scope = 'universal'
    """)
    universal_count = universal_rows[0]["n"] if universal_rows else 0

    if sl_count == 0:
        state = "cold_start"
    elif sl_count < 3:
        state = "learning"
    else:
        state = "learned"

    return {
        "count": sl_count,
        "cognitive_state": state,
        "service_line": service_line,
        "has_universal": universal_count > 0,
    }
'''
    code = code.rstrip() + new_fn
    p.write_text(code, encoding="utf-8")
    print("Added voice_coverage() helper to library.py")

# Test
import sys
for mod in list(sys.modules):
    if "library" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
from app.cognitive import library

print()
print("Testing voice_coverage for each service line:")
for sl in ["nri_tax", "foreign_subsidiary", "transfer_pricing", "audit", None]:
    r = library.voice_coverage(sl)
    print(f"  {str(sl):25s} | count={r['count']:2d} | state={r['cognitive_state']:12s} | has_universal={r['has_universal']}")
