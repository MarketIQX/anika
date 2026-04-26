from app.auth.passwords import hash_password
from app.db import execute, fetch_one

# AK
hashed = hash_password('MarketIQX@Ashish2026')
execute('UPDATE users SET password_hash=? WHERE email=?', (hashed, 'aks@marketiqx.com'))

# Prakash sir
hashed2 = hash_password('Welcome2026')
execute('UPDATE users SET password_hash=? WHERE email=?', (hashed2, 'prakasha@balakrishnaandco.com'))

print('Both passwords reset.')
for u in ['aks@marketiqx.com', 'prakasha@balakrishnaandco.com']:
    r = fetch_one('SELECT email FROM users WHERE email=?', (u,))
    print('  OK:', r['email'])
