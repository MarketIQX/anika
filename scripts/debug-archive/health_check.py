"""Diagnostic: is Anika alive, responsive, healthy?"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import urllib.request
import urllib.error
from app.db import fetch_all, fetch_one

print("=" * 70)
print("ANIKA HEALTH CHECK")
print("=" * 70)
print()

# 1. Is the server responding?
print("1. Server responding:")
endpoints = ["/healthz", "/", "/drafts", "/inbox", "/train", "/teaching-dashboard", "/analytics", "/settings"]
for path in endpoints:
    url = f"http://127.0.0.1:8000{path}"
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "diagnostic"})
        resp = urllib.request.urlopen(req, timeout=10)
        elapsed = time.time() - start
        print(f"   {path:25s} | {resp.status} | {elapsed:.2f}s | {len(resp.read())} bytes")
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        print(f"   {path:25s} | HTTP {e.code} | {elapsed:.2f}s | {e.reason}")
    except urllib.error.URLError as e:
        elapsed = time.time() - start
        print(f"   {path:25s} | NO RESPONSE | {elapsed:.2f}s | {e.reason}")
    except TimeoutError:
        elapsed = time.time() - start
        print(f"   {path:25s} | TIMEOUT | {elapsed:.2f}s")

# 2. Recent reasoning_log errors?
print()
print("2. Recent agent errors (last 100 reasoning_log entries):")
errors = fetch_all("""
    SELECT agent_name, status, substr(error_text, 1, 150) AS err, created_at
      FROM reasoning_log
     WHERE status != 'ok'
     ORDER BY id DESC LIMIT 10
""")
print(f"   Total non-ok: {len(errors)}")
for e in errors:
    print(f"   {e['created_at'][:19]} | {e['agent_name']:20s} | {e['status']:10s} | {e['err'] or '-'}")

# 3. Latency of recent agent calls
print()
print("3. Recent agent latency (last 20 calls):")
latencies = fetch_all("""
    SELECT agent_name, latency_ms, status, created_at
      FROM reasoning_log
     ORDER BY id DESC LIMIT 20
""")
for l in latencies:
    ms = l['latency_ms'] or 0
    flag = "SLOW" if ms > 5000 else ("warn" if ms > 2000 else "ok")
    print(f"   {l['created_at'][11:19]} | {l['agent_name']:20s} | {ms:6d}ms | {flag}")

# 4. Background poll loop alive?
print()
print("4. Recent Gmail poll activity:")
polls = fetch_all("""
    SELECT created_at, output_json
      FROM reasoning_log
     WHERE agent_name IN ('outbound_harvester', 'orchestrator')
     ORDER BY id DESC LIMIT 5
""")
for p in polls:
    print(f"   {p['created_at'][:19]} | {(p['output_json'] or '')[:80]}")
