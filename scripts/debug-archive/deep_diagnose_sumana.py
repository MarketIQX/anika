from app.db import fetch_all, fetch_one
import json

# Get the full reasoning_log entry for Sumana's failed enrichment
print("=" * 80)
print("SUMANA'S ENRICHER ATTEMPT — full trace")
print("=" * 80)
attempts = fetch_all("""
    SELECT id, status, error_text, input_json, output_json, reasoning_text, latency_ms, created_at
      FROM reasoning_log
     WHERE agent_name = 'enricher'
       AND email_id = 877
     ORDER BY id DESC
""")
print(f"Found {len(attempts)} enricher attempts on Sumana's email")
for a in attempts:
    print()
    print(f"Attempt id={a['id']} at {a['created_at']}")
    print(f"  Status: {a['status']}")
    print(f"  Latency: {a['latency_ms']}ms")
    print(f"  Error: {(a['error_text'] or '-')[:300]}")
    print(f"  Input: {(a['input_json'] or '')[:400]}")
    print(f"  Output: {(a['output_json'] or '')[:400]}")
    print(f"  Reasoning: {(a['reasoning_text'] or '')[:400]}")

# Check what the Enricher's tools actually return for Sumana's data
print()
print("=" * 80)
print("WHAT DO THE TOOLS RETURN FOR SUMANA?")
print("=" * 80)

# 1. lookup_client
from app.tools import client_tool
print()
print("1. tool_lookup_client('sumana.d@gmail.com'):")
client = client_tool.lookup_client('sumana.d@gmail.com')
print(f"   Returns: {client}")

# 2. retrieve_similar_drafts (memory_tool semantic search)
from app.tools import memory_tool
print()
print("2. semantic_search for Sumana's content:")
sims = memory_tool.semantic_search(
    query="Do you also help with taxation issues in the UK as a result of assets or income in India?",
    top_k=4,
)
print(f"   Found {len(sims)} similar:")
for s in sims:
    print(f"     id={s['id']} | {s.get('kind', '-'):15s} | dist={s.get('distance', 0):.3f} | {(s.get('subject') or '')[:50]}")

# 3. Check if there's a tool_get_routing_partner — what does it expect/return
print()
print("3. tool_get_routing_partner for nri_tax / foreign_subsidiary:")
import importlib
# Find routing_tool
import os
for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if not d.startswith('__')]
    for f in files:
        if "routing" in f.lower() or "partner" in f.lower():
            print(f"   File found: {os.path.join(root, f)}")

# Also pull the actual classification from earlier
print()
print("=" * 80)
print("CLASSIFICATION trail for Sumana")
print("=" * 80)
cls = fetch_one("SELECT * FROM classifications WHERE email_id = 877")
if cls:
    for k in cls.keys():
        print(f"  {k}: {(str(cls[k]) or '')[:200]}")
