from app.db import fetch_all, fetch_one

print('=== DB STATE ===')
tables = ['raw_emails', 'classifications', 'enrichments', 'drafts', 'approvals', 'sent_log', 'reasoning_log', 'memory', 'firm_knowledge', 'rules', 'agent_prompts', 'clients']
for t in tables:
    r = fetch_one('SELECT COUNT(*) as c FROM ' + t)
    print('  ' + t + ':', r['c'], 'rows')

print()
print('=== DRAFTS BY STATUS ===')
rows = fetch_all('SELECT sent_status, COUNT(*) as c FROM drafts GROUP BY sent_status')
for r in rows:
    print(' ', r['sent_status'], ':', r['c'])

print()
print('=== RAW EMAILS DATE RANGE ===')
r = fetch_one('SELECT MIN(received_at) as oldest, MAX(received_at) as newest FROM raw_emails')
print('  Oldest:', r['oldest'])
print('  Newest:', r['newest'])

print()
print('=== CLASSIFICATIONS DATE RANGE ===')
r2 = fetch_one('SELECT MIN(created_at) as oldest, MAX(created_at) as newest FROM classifications')
print('  Oldest:', r2['oldest'])
print('  Newest:', r2['newest'])
