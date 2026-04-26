from app.db import fetch_all, fetch_one

# Drafts schema first
print("DRAFTS TABLE SCHEMA:")
print("-" * 70)
for c in fetch_all("PRAGMA table_info(drafts)"):
    print(f"  {c['name']:25s} | {c['type']:10s}")

print()
print("DRAFTS IN LAST 24 HOURS:")
print("-" * 70)
# Try common status column names
try:
    drafts = fetch_all("""
        SELECT id, created_at, approval_status
          FROM drafts
         WHERE created_at > datetime('now', '-24 hours')
         ORDER BY id DESC LIMIT 10
    """)
    for d in drafts:
        print(f"  draft {d['id']:3d} | {d['approval_status']:20s} | {d['created_at'][:19]}")
except Exception as e:
    print(f"  approval_status failed: {e}")
    # Try without status
    drafts = fetch_all("""
        SELECT id, created_at FROM drafts
         WHERE created_at > datetime('now', '-24 hours')
         ORDER BY id DESC LIMIT 10
    """)
    for d in drafts:
        print(f"  draft {d['id']:3d} | {d['created_at'][:19]}")

# Queue 18 + 19 full content
print()
print("CONTENT OF QUEUE 18 (weak extraction suspected):")
print("-" * 70)
q18 = fetch_one("""
    SELECT id, raw_content, file_mime, original_filename, source_type
      FROM teaching_queue WHERE id = 18
""")
if q18:
    print(f"  source_type: {q18['source_type']}")
    print(f"  file_mime: {q18['file_mime']}")
    print(f"  filename: {q18['original_filename']}")
    print(f"  content (full):")
    print(f"    {q18['raw_content']}")

print()
print("CONTENT OF QUEUE 19:")
print("-" * 70)
q19 = fetch_one("""
    SELECT id, raw_content, file_mime, original_filename, source_type
      FROM teaching_queue WHERE id = 19
""")
if q19:
    print(f"  source_type: {q19['source_type']}")
    print(f"  file_mime: {q19['file_mime']}")
    print(f"  filename: {q19['original_filename']}")
    print(f"  content (first 500 chars):")
    print(f"    {q19['raw_content'][:500]}")
