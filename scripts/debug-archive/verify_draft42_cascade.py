from app.db import fetch_all, fetch_one

print("=" * 70)
print("DRAFT 42 — full cognitive cascade verification")
print("=" * 70)

# Draft state
d = fetch_one("""
    SELECT d.id, d.sent_status, d.cognitive_state, d.voice_coverage_count,
           d.parent_draft_id, d.created_at, d.updated_at,
           e.likely_service_line, re.from_email
      FROM drafts d
      LEFT JOIN enrichments e ON e.email_id = d.email_id
      LEFT JOIN raw_emails re ON re.id = d.email_id
     WHERE d.id = 42
""")
if d:
    print(f"Draft 42: status={d['sent_status']}, state={d['cognitive_state']}")
    print(f"  parent_draft_id={d['parent_draft_id']}")
    print(f"  service_line={d['likely_service_line']}, from={d['from_email']}")
    print(f"  created={d['created_at'][:19]}, updated={d['updated_at'][:19]}")
print()

# Approval recorded?
a = fetch_one("SELECT id, decision, decided_by, edit_instruction, created_at FROM approvals WHERE draft_id = 42")
if a:
    print(f"Approval: decision={a['decision']}, by={a['decided_by']}")
    print(f"  edit_instruction: {(a['edit_instruction'] or '')[:200]}")

# Sent log entry?
s = fetch_one("SELECT id, to_email, sent_at, test_mode FROM sent_log WHERE draft_id = 42")
if s:
    print(f"Sent: to={s['to_email']}, at={s['sent_at'][:19]}, test_mode={s['test_mode']}")
else:
    print("Sent: not yet (or didn't reach Gmail)")
print()

# Did journey metric land?
print("=" * 70)
print("Phase 1C-1: draft_metrics for this email")
print("=" * 70)
metric = fetch_one("""
    SELECT id, email_id, chain_length, edit_distance, outcome, created_at
      FROM draft_metrics
     WHERE email_id = (SELECT email_id FROM drafts WHERE id = 42)
""")
if metric:
    print(f"  Metric: chain_length={metric['chain_length']}, edit_distance={metric['edit_distance']:.3f}")
    print(f"  outcome={metric['outcome']}, at={metric['created_at'][:19]}")
else:
    print("  No metric row yet")
print()

# Did pattern miner detect any patterns?
print("=" * 70)
print("Phase 1C-2: patterns from this approval")
print("=" * 70)
patterns = fetch_all("""
    SELECT id, pattern_kind, pattern_text, journey_count, status, created_at
      FROM patterns_log
     WHERE julianday('now') - julianday(created_at) < (4.0 / 24.0)
     ORDER BY id DESC LIMIT 10
""")
print(f"  Recent patterns (last 4h): {len(patterns)}")
for p in patterns:
    text = (p['pattern_text'] or '')[:60]
    print(f"    {p['pattern_kind']:8s} | {p['status']:10s} | seen {p['journey_count']}x | '{text}'")
print()

# Was a voice_example saved?
print("=" * 70)
print("Voice library — recent harvests / saves")
print("=" * 70)
voices = fetch_all("""
    SELECT id, harvest_source, service_line, created_by, created_at,
           substr(content, 1, 100) AS preview
      FROM knowledge_library
     WHERE is_active = 1 AND purpose = 'voice_example'
       AND julianday('now') - julianday(created_at) < (4.0 / 24.0)
     ORDER BY id DESC
""")
print(f"  Recent voice examples (last 4h): {len(voices)}")
for v in voices:
    print(f"    id={v['id']} | source={v['harvest_source']} | sl={v['service_line']}")
    print(f"      preview: {v['preview']}")
