from app.db import fetch_one, execute

# Check library id=25 (the NRI voice_example)
r = fetch_one("SELECT id, content FROM knowledge_library WHERE id = 25")
print("Library id=25 (NRI voice_example) — last 300 chars:")
print(r["content"][-300:])
print()

# Strip signature markers from voice_examples in library
content = r["content"] or ""
markers = [
    "\nWarm regards,",
    "\nBest regards,",
    "\nYours faithfully,",
    "\nRegards,",
    "\nSincerely,",
    "\nS V Prakasha",
    "\nCA Prakasha",
    "\nCA S V Prakasha",
]
cut_at = len(content)
for m in markers:
    idx = content.find(m)
    if idx >= 0 and idx < cut_at:
        cut_at = idx

if cut_at < len(content):
    new_content = content[:cut_at].rstrip()
    execute("UPDATE knowledge_library SET content = ? WHERE id = 25", (new_content,))
    print(f"STRIPPED signature from library id=25")
    print(f"  Removed: {content[cut_at:cut_at+150]}...")
    print()
    r2 = fetch_one("SELECT content FROM knowledge_library WHERE id = 25")
    print("After strip — last 200 chars:")
    print(r2["content"][-200:])
else:
    print("No signature found to strip")
