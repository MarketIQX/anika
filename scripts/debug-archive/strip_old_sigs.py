from app.db import fetch_all, execute
from app.config.firm_identity import SIGNATURE_BLOCK

# Identify exemplars with old signature pattern
rows = fetch_all("""
    SELECT id, subject, content
      FROM memory
     WHERE kind = 'exemplar'
""")

# Heuristic: trim everything from "Warm regards," onwards
# These old exemplars end with salesy signatures that clash with locked signature
stripped_count = 0
for r in rows:
    content = r["content"] or ""
    # Find signature markers — trim from there
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
        execute("UPDATE memory SET content = ? WHERE id = ?", (new_content, r["id"]))
        stripped_count += 1
        print(f"STRIPPED id={r['id']} ({r['subject'][:50]}):")
        print(f"  Removed: {content[cut_at:cut_at+100]}...")
        print()

print(f"Total stripped: {stripped_count}")

# Verify id=6 now
from app.db import fetch_one
r = fetch_one("SELECT content FROM memory WHERE id = 6")
print()
print("Memory id=6 content AFTER strip (last 300 chars):")
print(r["content"][-300:])
