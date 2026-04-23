from app.db import fetch_one, fetch_all

r = fetch_one('SELECT COUNT(*) as c, MIN(received_at) as oldest, MAX(received_at) as newest FROM raw_emails')
print('Total emails:', r['c'])
print('Oldest:', r['oldest'])
print('Newest:', r['newest'])
print()

# Check Gmail filter
import re
with open('app/tools/gmail_tool.py') as f:
    content = f.read()
match = re.search(r'query: str = \"([^\"]+)\"', content)
if match:
    print('Gmail query filter:', match.group(1))
