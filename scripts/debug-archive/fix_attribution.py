from app.db import execute, fetch_one
execute(
    "UPDATE knowledge_library SET created_by = ? WHERE id = 25",
    ("prakasha@balakrishnaandco.com",),
)
r = fetch_one("SELECT id, created_by FROM knowledge_library WHERE id = 25")
print(f"Updated: library id=25 now created_by={r['created_by']}")
