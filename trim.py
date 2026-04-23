import sqlite3
from app.config import get_settings
settings = get_settings()
conn = sqlite3.connect(str(settings.db_path))
conn.execute('PRAGMA foreign_keys = OFF')
from datetime import datetime, timedelta
cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'

before = conn.execute('SELECT COUNT(*) FROM raw_emails').fetchone()[0]
print('Before:', before)

conn.execute('DELETE FROM raw_emails WHERE received_at < ?', (cutoff,))
conn.commit()

after = conn.execute('SELECT COUNT(*) FROM raw_emails').fetchone()[0]
print('After:', after)

r = conn.execute('SELECT MIN(received_at), MAX(received_at) FROM raw_emails').fetchone()
print('Oldest:', r[0])
print('Newest:', r[1])

conn.execute('PRAGMA foreign_keys = ON')
conn.close()
