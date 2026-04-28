"""Find what /knowledge-graph route does, find the slow code path."""
from pathlib import Path
import re

routes = Path("app/dashboard/routes.py").read_text(encoding="utf-8")

# Find the knowledge_graph function
m = re.search(r"async def knowledge_graph\(.+?(?=\n@router\.|^def |^async def |\Z)", routes, re.DOTALL | re.MULTILINE)
if m:
    code = m.group()
    print("=" * 70)
    print("knowledge_graph route (first 5000 chars):")
    print("=" * 70)
    print(code[:5000])
