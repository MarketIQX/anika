from pathlib import Path
import re

p = Path("app/agents/drafter.py")
code = p.read_text(encoding="utf-8")

# Find where the draft is INSERTed — that's where we need to write cognitive_state
# Look for INSERT INTO drafts
insert_matches = list(re.finditer(r'INSERT INTO drafts', code))
print(f"Found {len(insert_matches)} INSERT INTO drafts occurrence(s)")
print()

for m in insert_matches:
    start = max(0, m.start() - 200)
    end = min(len(code), m.end() + 800)
    print(f"--- Match at position {m.start()} ---")
    print(code[start:end])
    print()
