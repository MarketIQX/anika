from app.auth import users
from app.db import fetch_one
users.set_password('aks@marketiqx.com', 'Anika@2026AK')
r = fetch_one('SELECT email, role, password_hash FROM users WHERE email=?', ('aks@marketiqx.com',))
print('email:', r['email'], 'role:', r['role'], 'has_password:', bool(r['password_hash']))
# Verify auth works
print('auth test:', users.authenticate('aks@marketiqx.com', 'Anika@2026AK'))
