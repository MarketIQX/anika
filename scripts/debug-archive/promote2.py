from app.db import execute, fetch_one
execute('UPDATE users SET role=? WHERE email=?', ('admin', 'prakasha@balakrishnaandco.com'))
r = fetch_one('SELECT email, role FROM users WHERE email=?', ('prakasha@balakrishnaandco.com',))
print('Now:', dict(r))
