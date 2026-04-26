from app.db import fetch_one, fetch_all, execute
from app.auth import users

email = "prasad@balakrishnaandco.com"
password = "Welcome2026"

# Check if account exists
existing = fetch_one("SELECT id, email, role, last_login_at FROM users WHERE email = ?", (email,))

if existing:
    print(f"User already exists:")
    print(f"  id:         {existing['id']}")
    print(f"  email:      {existing['email']}")
    print(f"  role:       {existing['role']}")
    print(f"  last_login: {existing['last_login_at']}")
    print()
    print("Action: ensuring role=admin and resetting password to Welcome2026")
    try:
        users.set_password(email, password)
        print("  Password reset successful via users.set_password")
    except Exception as e:
        import bcrypt
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        execute("UPDATE users SET password_hash = ? WHERE email = ?", (pw_hash, email))
        print(f"  Password reset via direct SQL (fallback): {e}")
    execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
    print("  Role set to admin")
else:
    try:
        users.create(email=email, password=password, role="admin")
        print(f"Created user: {email} / {password} (admin role)")
    except Exception as e:
        print(f"users.create failed: {e}")
        import bcrypt
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        execute(
            "INSERT INTO users (email, role, password_hash) VALUES (?, 'admin', ?)",
            (email, pw_hash),
        )
        print(f"Created via direct SQL (fallback)")

# Verify
print()
print("=" * 70)
print("VERIFICATION")
print("=" * 70)
try:
    result = users.authenticate(email, password)
    if result:
        print(f"  PASS — authentication works")
        print(f"    user.email:    {result.email}")
        print(f"    user.role:     {result.role}")
        print(f"    user.is_admin: {result.is_admin}")
    else:
        print(f"  FAIL — users.authenticate returned None")
except Exception as e:
    print(f"  FAIL — exception: {e}")

print()
print("All users in system:")
for r in fetch_all("SELECT id, email, role, last_login_at FROM users ORDER BY id"):
    last = r['last_login_at'][:19] if r['last_login_at'] else 'never'
    print(f"  {r['id']:2d} | {r['email']:40s} | {r['role']:8s} | last login: {last}")
