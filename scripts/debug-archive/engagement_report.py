from app.db import fetch_all
from datetime import datetime, timezone
from collections import Counter, defaultdict

now = datetime.now(timezone.utc)
print(f"Engagement report — {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print("=" * 80)

PARTNERS = [
    ("prakasha@balakrishnaandco.com", "Prakash sir"),
    ("prasad@balakrishnaandco.com", "Prasad sir"),
]

for email, label in PARTNERS:
    print()
    print("=" * 80)
    print(f"  {label}")
    print("=" * 80)

    # All page visits
    visits = fetch_all("""
        SELECT created_at, target
          FROM access_log
         WHERE user_email = ? AND action = 'page_visit'
         ORDER BY id ASC
    """, (email,))

    if not visits:
        print(f"  (no page visits recorded — middleware was added on Apr 25, 12:51 UTC)")
        continue

    print(f"  Total page visits: {len(visits)}")
    earliest = visits[0]['created_at'][:19]
    latest = visits[-1]['created_at'][:19]
    print(f"  Tracking window: {earliest} -> {latest} UTC")

    # ===== 1. PAGES BY VISIT COUNT =====
    print()
    print(f"  TOP PAGES (by visit count)")
    print(f"  " + "-" * 76)
    page_counts = Counter(v['target'] for v in visits)
    for path, count in page_counts.most_common(15):
        bar = "█" * min(count, 40)
        print(f"    {count:3d} | {path:40s} {bar}")

    # ===== 2. SECTION-LEVEL AGGREGATION =====
    print()
    print(f"  SECTIONS (grouped)")
    print(f"  " + "-" * 76)
    section_counts = Counter()
    for v in visits:
        path = v['target'] or '/'
        if path == '/' or path == '':
            section = 'home'
        elif path.startswith('/drafts'):
            section = 'Drafts (incl. individual draft pages)'
        elif path.startswith('/train/rules'):
            section = 'Rules Management'
        elif path.startswith('/train'):
            section = 'Train tab'
        elif path.startswith('/teaching-dashboard'):
            section = 'Progress / Teaching Dashboard'
        elif path.startswith('/knowledge-graph'):
            section = 'Knowledge Graph'
        elif path.startswith('/inbox'):
            section = 'Inbox'
        elif path.startswith('/analytics'):
            section = 'Analytics'
        elif path.startswith('/settings'):
            section = 'Settings'
        elif path.startswith('/account'):
            section = 'Account'
        else:
            section = 'Other'
        section_counts[section] += 1

    total = sum(section_counts.values())
    for section, count in section_counts.most_common():
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"    {count:3d} ({pct:5.1f}%) | {section:40s} {bar}")

    # ===== 3. SPECIFIC DRAFTS OPENED =====
    print()
    print(f"  INDIVIDUAL DRAFTS OPENED")
    print(f"  " + "-" * 76)
    draft_visits = Counter()
    for v in visits:
        path = v['target'] or ''
        if path.startswith('/drafts/') and path != '/drafts/':
            # Extract draft id
            parts = path.split('/')
            if len(parts) >= 3 and parts[2].isdigit():
                draft_visits[parts[2]] += 1
    if not draft_visits:
        print(f"    (no individual draft pages opened)")
    else:
        for draft_id, count in sorted(draft_visits.items(), key=lambda x: int(x[0])):
            label_marker = "(re-read)" if count > 1 else ""
            print(f"    Draft {draft_id} : {count} visit(s) {label_marker}")

    # ===== 4. TIME-OF-DAY HEATMAP =====
    print()
    print(f"  ACTIVITY BY HOUR (UTC; add 5:30 for IST)")
    print(f"  " + "-" * 76)
    hour_counts = Counter()
    for v in visits:
        hour = int(v['created_at'][11:13])
        hour_counts[hour] += 1
    for h in range(24):
        count = hour_counts.get(h, 0)
        bar = "█" * count
        ist_h = (h + 5) % 24
        ist_min = "30"
        print(f"    {h:02d}:00 UTC ({ist_h:02d}:{ist_min} IST) | {count:3d} | {bar}")

    # ===== 5. SESSION SUMMARIES =====
    print()
    print(f"  SESSIONS (gaps > 30 min = new session)")
    print(f"  " + "-" * 76)
    sessions = []
    if visits:
        cur_session = {'start': visits[0]['created_at'], 'end': visits[0]['created_at'], 'pages': [visits[0]['target']]}
        from datetime import datetime as _dt
        for v in visits[1:]:
            prev_t = _dt.fromisoformat(cur_session['end'].replace('Z', '+00:00'))
            cur_t = _dt.fromisoformat(v['created_at'].replace('Z', '+00:00'))
            gap_min = (cur_t - prev_t).total_seconds() / 60
            if gap_min > 30:
                sessions.append(cur_session)
                cur_session = {'start': v['created_at'], 'end': v['created_at'], 'pages': [v['target']]}
            else:
                cur_session['end'] = v['created_at']
                cur_session['pages'].append(v['target'])
        sessions.append(cur_session)

    print(f"    Total sessions: {len(sessions)}")
    for i, s in enumerate(sessions[-5:], 1):  # last 5 sessions
        from datetime import datetime as _dt
        start = _dt.fromisoformat(s['start'].replace('Z', '+00:00'))
        end = _dt.fromisoformat(s['end'].replace('Z', '+00:00'))
        dur = (end - start).total_seconds() / 60
        print(f"    Session {i}: {s['start'][:19]} -> {s['end'][:19]} | {len(s['pages'])} pages | ~{dur:.1f} min")
