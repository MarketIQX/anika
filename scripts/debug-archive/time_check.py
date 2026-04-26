from app.db import fetch_one
from datetime import datetime, timezone
r = fetch_one("SELECT datetime('now') AS db_now")
print(f"Python UTC now:       {datetime.now(timezone.utc)}")
print(f"SQLite datetime(now): {r['db_now']}")
print(f"Python local now:     {datetime.now()}")

# Also — look at the actual created_at format to see what timezone it's stored in
r2 = fetch_one("SELECT created_at FROM access_log ORDER BY id DESC LIMIT 1")
print(f"Latest access_log.created_at: {r2['created_at']}")
