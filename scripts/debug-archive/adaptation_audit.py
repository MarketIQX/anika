from app.db import fetch_all, fetch_one
from pathlib import Path
import re

print("=" * 80)
print("ADAPTATION CAPABILITY AUDIT")
print("=" * 80)

# STEP 1 — Does Anika capture edits?
print()
print("1. EDIT SIGNAL CAPTURE")
print("-" * 80)
# Find draft 23 and 24 — was the edit relationship stored?
d24 = fetch_one("SELECT id, parent_draft_id, body, subject FROM drafts WHERE id=24")
d23 = fetch_one("SELECT id, body, subject FROM drafts WHERE id=23")
if d24 and d24['parent_draft_id']:
    print(f"  Draft 24 has parent_draft_id={d24['parent_draft_id']} -> edit chain IS captured")
else:
    print(f"  Draft 24 parent_draft_id={d24.get('parent_draft_id') if d24 else 'N/A'}")

# STEP 2 — Does anything classify the edit?
print()
print("2. EDIT CLASSIFICATION")
print("-" * 80)
# Look for learner invocations on edits
edit_log = fetch_all("""
    SELECT id, agent, summary, created_at
      FROM reasoning_log
     WHERE agent = 'learner'
        OR summary LIKE '%edit%'
     ORDER BY id DESC
     LIMIT 10
""")
if edit_log:
    for e in edit_log:
        print(f"  {e['created_at'][:19]} | {e['agent']:10s} | {(e['summary'] or '')[:90]}")
else:
    print("  No learner invocations found in reasoning_log")

# Check if learner.py exists and what it does on edits
learner_path = Path("app/agents/learner.py")
if learner_path.exists():
    lc = learner_path.read_text(encoding="utf-8")
    has_edit_handler = "edit" in lc.lower() and "classify" in lc.lower()
    print(f"  app/agents/learner.py exists — handles edits: {has_edit_handler}")

# STEP 3 — Was anything STORED from the edit?
print()
print("3. EDIT -> STORAGE (did the edit teach anything?)")
print("-" * 80)
# New library entries created AFTER draft 24 was edited (08:24)
post_edit = fetch_all("""
    SELECT id, purpose, content, created_at, created_by
      FROM knowledge_library
     WHERE is_active=1
       AND created_at > '2026-04-24T08:24:00'
     ORDER BY id
""")
if post_edit:
    print("  Library entries created AFTER the edit:")
    for e in post_edit:
        print(f"    id={e['id']} | {e['purpose']:20s} | {(e['content'] or '')[:70]}")
else:
    print("  No new library entries since draft 24 was edited")

# STEP 4 — Will Drafter USE the voice_example next time?
print()
print("4. RETRIEVAL — does Drafter actually use voice_examples?")
print("-" * 80)
# Check the drafter prompt assembly path
drafter_path = Path("app/agents/drafter.py")
if drafter_path.exists():
    dc = drafter_path.read_text(encoding="utf-8")
    uses_examples = "retrieve_examples" in dc
    uses_rules = "retrieve_rules" in dc
    uses_facts = "retrieve_facts" in dc
    print(f"  Drafter calls retrieve_rules():    {uses_rules}")
    print(f"  Drafter calls retrieve_examples(): {uses_examples}")
    print(f"  Drafter calls retrieve_facts():    {uses_facts}")

# Check: does retrieve_examples filter by purpose=voice_example?
lib_path = Path("app/cognitive/library.py")
if lib_path.exists():
    lc = lib_path.read_text(encoding="utf-8")
    if "k.kind = 'example'" in lc and "k.purpose IN" in lc:
        print("  retrieve_examples DOES filter by purpose IN draftable set")
        print("  -> voice_example entries WILL be pulled for future drafts")
    else:
        print("  retrieve_examples may not be purpose-filtered")

# STEP 5 — Voice examples currently available to Drafter
print()
print("5. VOICE ARSENAL — what voices Anika has today")
print("-" * 80)
voices = fetch_all("""
    SELECT id, service_line, created_by, substr(content, 1, 80) preview
      FROM knowledge_library
     WHERE is_active=1
       AND purpose = 'voice_example'
""")
print(f"  {len(voices)} voice_example entries in library:")
for v in voices:
    user = (v['created_by'] or '?').split('@')[0]
    sl = v['service_line'] or '-'
    print(f"    id={v['id']} | {sl:20s} | by {user:10s} | {v['preview']}")

# STEP 6 — Per service_line voice coverage
print()
print("6. VOICE COVERAGE BY SERVICE LINE")
print("-" * 80)
coverage = fetch_all("""
    SELECT service_line, COUNT(*) n
      FROM knowledge_library
     WHERE is_active=1 AND purpose='voice_example'
     GROUP BY service_line
""")
if coverage:
    for r in coverage:
        print(f"    {r['service_line'] or 'universal':20s} | {r['n']} voice examples")
else:
    print("    None")

# STEP 7 — Does the edit itself become a voice example automatically?
print()
print("7. EDIT -> VOICE_EXAMPLE AUTOMATION")
print("-" * 80)
# Check if there's any code that promotes an edited draft into a voice_example
for mod_path in ["app/agents/learner.py", "app/cognitive/learning_engine.py"]:
    p = Path(mod_path)
    if not p.exists():
        continue
    content = p.read_text(encoding="utf-8")
    promotes = "voice_example" in content and ("add_entry" in content or "INSERT INTO knowledge_library" in content)
    print(f"  {mod_path}: promotes edit to voice_example = {promotes}")

# STEP 8 — applied_count on the NEW voice_example (id=24)
print()
print("8. HAS THE NEW VOICE_EXAMPLE BEEN USED YET?")
print("-" * 80)
v24 = fetch_one("SELECT id, applied_count, last_used_at FROM knowledge_library WHERE id=24")
if v24:
    print(f"  voice_example id=24: applied_count={v24['applied_count']}, last_used={v24['last_used_at']}")
    if v24['applied_count'] == 0:
        print("  (not used yet — next NRI enquiry will trigger retrieval)")
