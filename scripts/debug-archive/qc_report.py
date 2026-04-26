from app.db import fetch_one, fetch_all
from datetime import datetime, timezone

now_utc = datetime.now(timezone.utc)
print(f"Now: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

# ============================================================
# 1. SYSTEM HEALTH — is Anika running & happy?
# ============================================================
print("=" * 70)
print("1. SYSTEM HEALTH")
print("=" * 70)

# Any errors in last 24h?
errors = fetch_all("""
    SELECT agent_name, error_text, created_at
      FROM reasoning_log
     WHERE status != 'ok'
       AND created_at > datetime('now', '-24 hours')
     ORDER BY id DESC LIMIT 5
""")
if not errors:
    print("  [OK] No agent errors in last 24 hours")
else:
    print(f"  [WARN] {len(errors)} errors in last 24 hours:")
    for e in errors:
        print(f"    {e['created_at'][11:19]} | {e['agent_name']} | {(e['error_text'] or '')[:80]}")

# Any stuck queue items?
stuck = fetch_all("""
    SELECT id, status, created_at, created_by_user
      FROM teaching_queue
     WHERE status IN ('pending', 'processing')
       AND julianday('now') - julianday(created_at) < 1
""")
if stuck:
    print(f"  [INFO] {len(stuck)} queues in non-terminal state:")
    for s in stuck:
        print(f"    queue {s['id']} | status={s['status']} | by {s['created_by_user']}")
else:
    print("  [OK] No stuck queue items")

# Drafting pause status
from app.db import fetch_one
paused = fetch_one("SELECT value FROM system_state WHERE key='drafting_paused'")
kill = fetch_one("SELECT value FROM system_state WHERE key='kill_switch'")
print(f"  drafting_paused: {paused['value'] if paused else 'off'}")
print(f"  kill_switch:     {kill['value'] if kill else 'off'}")

# ============================================================
# 2. PRAKASH SIR ACTIVITY
# ============================================================
print()
print("=" * 70)
print("2. PRAKASH SIR ACTIVITY")
print("=" * 70)

latest = fetch_one("""
    SELECT created_at, action,
           CAST((julianday('now') - julianday(created_at)) * 24 * 60 AS INTEGER) AS minutes_ago
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
     ORDER BY id DESC LIMIT 1
""")
if latest:
    mins = latest['minutes_ago']
    hrs = mins // 60
    m_rem = mins % 60
    print(f"  Last event: {latest['action']} at {latest['created_at'][:19]} UTC")
    print(f"  That was {hrs}h {m_rem}m ago")
    print()

# Events since the message sent (around 10:00 UTC = 15:30 IST)
msg_sent = "2026-04-24T10:00:00"
events_since = fetch_all(f"""
    SELECT created_at, action
      FROM access_log
     WHERE user_email = 'prakasha@balakrishnaandco.com'
       AND created_at > '{msg_sent}'
     ORDER BY id DESC
""")
print(f"  Events SINCE your WhatsApp message (~{msg_sent[:10]} 10:00 UTC / 15:30 IST):")
if not events_since:
    print("    None — he hasn't logged in since the message")
else:
    for e in events_since:
        print(f"    {e['created_at'][11:19]} | {e['action']}")

# ============================================================
# 3. DRAFTS STATE
# ============================================================
print()
print("=" * 70)
print("3. DRAFTS STATE")
print("=" * 70)

drafts = fetch_all("""
    SELECT id, sent_status, parent_draft_id, created_at
      FROM drafts
     WHERE julianday('now') - julianday(created_at) < 1
     ORDER BY id DESC
""")
if not drafts:
    print("  No drafts in last 24h")
else:
    for d in drafts:
        parent = f" (edit of #{d['parent_draft_id']})" if d['parent_draft_id'] else ""
        print(f"  draft {d['id']:3d} | {d['sent_status']:20s} | {d['created_at'][:19]}{parent}")

# ============================================================
# 4. LIBRARY & LEARNING
# ============================================================
print()
print("=" * 70)
print("4. LIBRARY STATE")
print("=" * 70)

total = fetch_one("SELECT COUNT(*) n FROM knowledge_library WHERE is_active = 1")
voices = fetch_one("SELECT COUNT(*) n FROM knowledge_library WHERE is_active = 1 AND purpose = 'voice_example'")
rules_count = fetch_one("SELECT COUNT(*) n FROM meta_rules WHERE is_active = 1")
print(f"  Active library entries: {total['n']}")
print(f"  Voice examples:         {voices['n']}")
print(f"  Active meta-rules:      {rules_count['n']}")

# Any new library entries since message time?
new = fetch_all(f"""
    SELECT id, purpose, service_line, created_by
      FROM knowledge_library
     WHERE is_active = 1
       AND created_at > '{msg_sent}'
""")
if new:
    print(f"  [CHANGE] {len(new)} new library entries since message:")
    for e in new:
        by = (e['created_by'] or '?').split('@')[0]
        print(f"    id={e['id']} | {e['purpose']} | {e['service_line'] or '-'} | by {by}")
else:
    print("  No new library entries since message")

# ============================================================
# 5. INCOMING ENQUIRIES
# ============================================================
print()
print("=" * 70)
print("5. INCOMING EMAIL TRAFFIC (last 24h)")
print("=" * 70)
emails = fetch_all("""
    SELECT id, from_email, subject, received_at
      FROM raw_emails
     WHERE julianday('now') - julianday(received_at) < 1
     ORDER BY id DESC LIMIT 10
""")
if not emails:
    print("  No emails received in last 24h")
else:
    print(f"  {len(emails)} emails received:")
    for e in emails:
        print(f"    {e['received_at'][11:19] if e['received_at'] else '-'} | {e['from_email'][:40]:40s} | {(e['subject'] or '')[:50]}")
