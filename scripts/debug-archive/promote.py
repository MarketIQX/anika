from app.auth import users
from app.db import fetch_one
# Promote Prakash sir
users.update_role('prakasha@balakrishnaandco.com', 'admin')
# Verify
r = fetch_one('SELECT email, role FROM users WHERE email=?', ('prakasha@balakrishnaandco.com',))
print('Now:', dict(r))
