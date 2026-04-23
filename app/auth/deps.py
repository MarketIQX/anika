"""FastAPI dependencies for auth.

Usage:

    from fastapi import Depends
    from app.auth.deps import require_user, require_admin

    @router.get("/secret")
    async def secret(user = Depends(require_user)):
        ...

Session data we store: just the user's email. We re-load the User from the
DB on every request (cheap SQLite lookup) so role changes take effect
immediately without forcing re-login.
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.auth import users
from app.auth.users import User

SESSION_KEY_EMAIL = "user_email"


def current_user(request: Request) -> User | None:
    """Return the logged-in User, or None if there's no valid session."""
    email = request.session.get(SESSION_KEY_EMAIL) if hasattr(request, "session") else None
    if not email:
        return None
    return users.get_by_email(email)


def require_user(request: Request) -> User:
    """Dependency — unauthenticated requests get redirected to /login.

    We raise a 307 redirect via HTTPException so any protected route works
    without boilerplate. Direct 302 also fine; we pick 307 to preserve method
    on POST forms (the login page handles that gracefully).
    """
    u = current_user(request)
    if u is None:
        # Redirect to login with a `next` query so we can come back afterward.
        next_url = request.url.path
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?next={next_url}"},
        )
    return u


def require_admin(request: Request) -> User:
    """Dependency — only admin role may proceed."""
    u = require_user(request)
    if not u.is_admin:
        # Not a redirect — this is an authorization failure, not authentication.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return u


def sign_in(request: Request, user: User) -> None:
    """Put the user's email on the session. Opposite of `sign_out`."""
    request.session[SESSION_KEY_EMAIL] = user.email


def sign_out(request: Request) -> None:
    """Clear the session."""
    request.session.clear()


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def client_ua(request: Request) -> str | None:
    return request.headers.get("user-agent")
