from app.db import fetch_all, fetch_one

print("=" * 80)
print("ANIKA LEARNING & ERROR ANALYSIS — Prakash sir's session today")
print("=" * 80)

# Accuracy — did Anika's proposals match user confirmations?
print()
print("1. CLASSIFICATION ACCURACY (Anika proposed vs user confirmed):")
print("-" * 80)
rows = fetch_all("""
    SELECT
        kl.id,
        kl.anika_proposed_purpose AS proposed,
        kl.user_confirmed_purpose AS confirmed,
        kl.anika_proposed_confidence AS conf,
        substr(kl.content, 1, 70) AS preview,
        kl.created_by
      FROM knowledge_library kl
     WHERE kl.is_active = 1
       AND kl.anika_proposed_purpose IS NOT NULL
       AND kl.user_confirmed_purpose IS NOT NULL
     ORDER BY kl.id DESC
""")
matches = 0
total = 0
for r in rows:
    total += 1
    match = r['proposed'] == r['confirmed']
    if match:
        matches += 1
    marker = "OK" if match else "CORRECTED"
    conf_pct = f"{r['conf']*100:.0f}%" if r['conf'] else "-"
    user = r['created_by'].split('@')[0]
    print(f"  [{marker:10s}] id={r['id']:3d} | {user:10s} | conf={conf_pct:5s} | {r['proposed']:20s} -> {r['confirmed']:20s}")
    print(f"              {r['preview']}")

if total > 0:
    pct = matches / total * 100
    print()
    print(f"  Accuracy: {matches}/{total} = {pct:.1f}% (Anika got it right on first try)")

# What did Prakash sir upload today?
print()
print()
print("2. TODAY'S TEACHING SESSION (Prakash sir, last 4 hours):")
print("-" * 80)
today = fetch_all("""
    SELECT
        tq.id AS qid,
        tq.anika_proposed_purpose AS proposed,
        tq.anika_proposed_confidence AS conf,
        tq.status,
        substr(tq.raw_content, 1, 100) AS preview,
        tq.created_at
      FROM teaching_queue tq
     WHERE tq.created_by_user = 'prakasha@balakrishnaandco.com'
       AND tq.created_at > datetime('now', '-4 hours')
     ORDER BY tq.id
""")
for r in today:
    conf = f"{r['conf']*100:.0f}%" if r['conf'] else "-"
    status = r['status']
    print(f"  queue {r['qid']:3d} | {status:10s} | {r['proposed'] or '-':20s} | conf={conf:5s} | {r['created_at'][11:19]}")
    print(f"              {r['preview']}")
    print()

# Humility layer — did Anika ever say "I don't know"?
print()
print("3. HUMILITY — did Anika ever express uncertainty today?")
print("-" * 80)
humble = fetch_all("""
    SELECT id, anika_proposed_purpose, anika_proposed_confidence, humility_articulation
      FROM teaching_queue
     WHERE created_by_user = 'prakasha@balakrishnaandco.com'
       AND humility_articulation IS NOT NULL
       AND created_at > datetime('now', '-4 hours')
""")
if not humble:
    print("  No humility-layer output today. Anika was >=50% confident on everything.")
else:
    for r in humble:
        print(f"  queue {r['id']}: {r['anika_proposed_purpose']} @ {r['anika_proposed_confidence']:.2f}")

# Meta-rules created from his corrections
print()
print("4. META-RULES CREATED TODAY (from Prakash sir's corrections):")
print("-" * 80)
rules = fetch_all("""
    SELECT id, rule_text, target_purpose, priority, created_by
      FROM meta_rules
     WHERE is_active = 1
       AND created_at > datetime('now', '-4 hours')
""")
if not rules:
    print("  No meta-rules. Either he agreed with Anika every time, or skipped rule saves.")
else:
    for r in rules:
        print(f"  rule {r['id']}: -> {r['target_purpose']}")
        print(f"    {r['rule_text'][:100]}")

# Errors in server log (from access_log failures)
print()
print("5. ERRORS OR FAILURES TODAY:")
print("-" * 80)
errors = fetch_all("""
    SELECT id, status, error_text, created_at
      FROM teaching_queue
     WHERE error_text IS NOT NULL
       AND created_at > datetime('now', '-4 hours')
""")
if not errors:
    print("  No teaching_queue errors.")
else:
    for r in errors:
        print(f"  queue {r['id']}: status={r['status']} | error={r['error_text'][:100]}")

# Drafts — is she actually drafting?
print()
print("6. DRAFT QUALITY INDICATORS (recent drafts):")
print("-" * 80)
drafts_summary = fetch_one("""
    SELECT
        SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) approved,
        SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) rejected,
        SUM(CASE WHEN status = 'edited' THEN 1 ELSE 0 END) edited,
        COUNT(*) total
      FROM drafts
     WHERE created_at > datetime('now', '-24 hours')
""")
if drafts_summary and drafts_summary['total']:
    print(f"  Drafts in last 24h: {drafts_summary['total']}")
    print(f"    approved: {drafts_summary['approved']}")
    print(f"    edited:   {drafts_summary['edited']}")
    print(f"    rejected: {drafts_summary['rejected']}")
else:
    print("  No new drafts in 24h. Either no incoming enquiries, or drafting paused.")

# Last few draft approve/edit/reject actions for signal on quality
recent_actions = fetch_all("""
    SELECT action, created_at, user_email
      FROM access_log
     WHERE action IN ('draft_approve','draft_edit','draft_reject')
       AND created_at > datetime('now', '-24 hours')
     ORDER BY id DESC LIMIT 10
""")
print()
print("  Recent draft actions:")
for r in recent_actions:
    user = r['user_email'].split('@')[0]
    print(f"    {r['created_at'][11:19]} | {user:10s} | {r['action']}")

# Library growth velocity
print()
print("7. LIBRARY GROWTH TODAY:")
print("-" * 80)
today_count = fetch_one("SELECT COUNT(*) n FROM knowledge_library WHERE is_active=1 AND created_at > datetime('now', '-1 day')")
total_count = fetch_one("SELECT COUNT(*) n FROM knowledge_library WHERE is_active=1")
print(f"  Library entries added TODAY:   {today_count['n']}")
print(f"  Library entries total:         {total_count['n']}")
