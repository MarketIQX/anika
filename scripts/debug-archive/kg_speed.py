import time
from app.db import fetch_all, fetch_one

print("Testing Knowledge Graph queries one by one...")
print()

# 1. Library entries with embeddings
t = time.time()
fetch_all("SELECT id, kind, content, service_line, purpose FROM knowledge_library WHERE is_active = 1")
print(f"  library entries:        {(time.time()-t)*1000:.0f}ms")

# 2. Memory entries
t = time.time()
fetch_all("SELECT id, kind, content, service_line FROM memory WHERE is_active = 1")
print(f"  memory entries:         {(time.time()-t)*1000:.0f}ms")

# 3. Rules
t = time.time()
fetch_all("SELECT id, rule_type, pattern FROM rules WHERE is_active = 1")
print(f"  rules:                  {(time.time()-t)*1000:.0f}ms")

# 4. Patterns
t = time.time()
fetch_all("SELECT id, pattern_text, status FROM patterns_log")
print(f"  patterns:               {(time.time()-t)*1000:.0f}ms")

# 5. Vector tables (these can be slow)
t = time.time()
fetch_all("SELECT COUNT(*) FROM knowledge_library_vec_rowids")
print(f"  vec rowids count:       {(time.time()-t)*1000:.0f}ms")

# 6. Counts on large tables
t = time.time()
fetch_one("SELECT COUNT(*) FROM raw_emails")
print(f"  raw_emails count:       {(time.time()-t)*1000:.0f}ms")

t = time.time()
fetch_one("SELECT COUNT(*) FROM reasoning_log")
print(f"  reasoning_log count:    {(time.time()-t)*1000:.0f}ms")
