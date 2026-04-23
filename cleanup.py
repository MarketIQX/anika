from app.db import execute, fetch_one
from datetime import datetime, timedelta

cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'

execute('DELETE FROM drafts WHERE email_id IN (SELECT id FROM raw_emails WHERE received_at < ?)', (cutoff,))
execute('DELETE FROM classifications WHERE email_id IN (SELECT id FROM raw_emails WHERE received_at < ?)', (cutoff,))
execute('DELETE FROM enrichments WHERE email_id IN (SELECT id FROM raw_emails WHERE received_at < ?)', (cutoff,))

r = fetch_one('SELECT COUNT(*) as c FROM classifications')
print('Classifications remaining:', r['c'])
r2 = fetch_one('SELECT COUNT(*) as c FROM drafts')
print('Drafts remaining:', r2['c'])
r3 = fetch_one('SELECT COUNT(*) as c FROM raw_emails')
print('Raw emails total (untouched):', r3['c'])
