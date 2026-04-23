from app.db import fetch_one

d = fetch_one('SELECT * FROM drafts WHERE email_id=(SELECT id FROM raw_emails WHERE from_email=?) ORDER BY id DESC LIMIT 1', ('chandrika.share@gmail.com',))
if not d:
    print('Chandrika draft not found')
else:
    print('Draft fields:')
    for k, v in dict(d).items():
        val = str(v)[:150] if v else v
        print('  ', k, ':', val)
