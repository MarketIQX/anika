from app.db import fetch_all
rows = fetch_all("SELECT id, status, anika_proposed_purpose, anika_proposed_confidence, created_at FROM teaching_queue ORDER BY id DESC LIMIT 5")
for r in rows:
    print(dict(r))
