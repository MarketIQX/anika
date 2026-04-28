import time
from app.db import fetch_all, fetch_one

print("Testing /train queries individually...")
print()

# Library entries
t = time.time()
fetch_all("SELECT * FROM knowledge_library WHERE is_active = 1")
print(f"  library entries:   {(time.time()-t)*1000:.0f}ms")

# Patterns
t = time.time()
fetch_all("SELECT * FROM patterns_log WHERE status = 'open'")
print(f"  open patterns:     {(time.time()-t)*1000:.0f}ms")

# Metrics
t = time.time()
fetch_all("SELECT * FROM draft_metrics ORDER BY id DESC LIMIT 50")
print(f"  recent metrics:    {(time.time()-t)*1000:.0f}ms")

# Pending queue
t = time.time()
fetch_all("SELECT * FROM teaching_queue WHERE awaiting_confirmation = 1")
print(f"  awaiting confirm:  {(time.time()-t)*1000:.0f}ms")

# Counts
t = time.time()
fetch_one("SELECT COUNT(*) FROM knowledge_library WHERE is_active = 1")
print(f"  library count:     {(time.time()-t)*1000:.0f}ms")
