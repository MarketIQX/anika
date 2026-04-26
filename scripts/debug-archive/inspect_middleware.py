from pathlib import Path
import re

# main.py — where FastAPI app is created and middleware registered
p = Path("app/main.py")
code = p.read_text(encoding="utf-8")
print(f"main.py size: {len(code)} chars")
print()

# Show where app is created and middleware
print("=" * 70)
print("App setup section (first 60 lines):")
print("=" * 70)
for i, line in enumerate(code.splitlines()[:60], 1):
    print(f"{i:3d}| {line}")

# Existing middleware
print()
print("=" * 70)
print("Existing middleware additions:")
print("=" * 70)
for m in re.finditer(r"app\.add_middleware\([^)]*\)", code, re.DOTALL):
    print(f"  {m.group()[:150]}")

# Also check auth/middleware.py for the existing auth middleware pattern
auth_mw = Path("app/auth/middleware.py")
if auth_mw.exists():
    print()
    print("=" * 70)
    print("auth/middleware.py — pattern to follow")
    print("=" * 70)
    print(auth_mw.read_text(encoding="utf-8")[:2000])

# Check access_log schema
print()
print("=" * 70)
print("access_log table schema")
print("=" * 70)
from app.db import fetch_all
cols = fetch_all("PRAGMA table_info(access_log)")
for c in cols:
    print(f"  {c['name']:20s} | {c['type']}")
