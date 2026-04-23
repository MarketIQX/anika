"""Login / logout / account routes + templates."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import access_log, users
from app.auth.deps import client_ip, client_ua, current_user, require_user, sign_in, sign_out
from app.auth.password_policy import validate_new_password
from app.auth.users import User
from app.guardrails import daily_cap, kill_switch
from app.config import get_settings
from app.tools import gmail_tool

TEMPLATES_DIR = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


def _safe_next(next_url: str | None) -> str:
    """Only allow relative paths — never an absolute URL (open-redirect guard)."""
    if not next_url:
        return "/drafts"
    # Reject scheme://host and protocol-relative //host, only allow single leading /.
    if next_url.startswith("//") or "://" in next_url or not next_url.startswith("/"):
        return "/drafts"
    return next_url


@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, next: str | None = None, error: str | None = None):
    # Already logged in? Bounce to the next page.
    if current_user(request):
        return RedirectResponse(_safe_next(next), status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "next": _safe_next(next),
            "error": error,
        },
    )


@router.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/drafts"),
):
    u = users.authenticate(email.strip(), password)
    if u is None:
        access_log.log(
            action="login_failure",
            user_email=email.strip().lower() or None,
            ip_address=client_ip(request),
            user_agent=client_ua(request),
        )
        # Re-render with generic error — we intentionally don't say "wrong user"
        # vs "wrong password".
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "next": _safe_next(next),
                "error": "Invalid email or password.",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    sign_in(request, u)
    users.touch_last_login(u.email)
    access_log.log(
        action="login_success",
        user_email=u.email,
        ip_address=client_ip(request),
        user_agent=client_ua(request),
    )
    return RedirectResponse(_safe_next(next), status_code=303)


@router.post("/logout")
async def logout(request: Request):
    u = current_user(request)
    if u:
        access_log.log(
            action="logout",
            user_email=u.email,
            ip_address=client_ip(request),
            user_agent=client_ua(request),
        )
    sign_out(request)
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------------------
# Self-service password change — /account.
# Available to both roles. Session is preserved on success.
# ---------------------------------------------------------------------------


def _account_context(request: Request, user: User, **extra) -> dict:
    """Build the context the base.html header expects (tabs, banners, user)."""
    ctx = {
        "request": request,
        "current_user": user,
        "gmail_connected": gmail_tool.has_credentials(),
        "kill_switch_on": kill_switch.is_on(),
        "cap_status": daily_cap.status(),
        "test_mode": get_settings().anika_test_mode,
        "active_tab": None,  # /account isn't a main tab
    }
    ctx.update(extra)
    return ctx


@router.get("/account", response_class=HTMLResponse)
async def account_get(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(
        request,
        "account.html",
        _account_context(request, user, errors=[], success=False),
    )


@router.post("/account/change-password", response_class=HTMLResponse)
async def account_change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: User = Depends(require_user),
):
    # 1. Verify the current password first. If this fails, we never look at
    #    the new one — that's both a UX signal ("your current-password
    #    entry is wrong") and a guard against someone with a hijacked
    #    session rotating the password without knowing the old one.
    stored_hash = users.get_password_hash(user.email)
    from app.auth.passwords import verify_password

    if not stored_hash or not verify_password(current_password, stored_hash):
        return templates.TemplateResponse(
            request,
            "account.html",
            _account_context(
                request, user,
                errors=["Current password is incorrect."],
                success=False,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 2. Validate the new password per policy.
    errors = validate_new_password(current_password, new_password, confirm_password)
    if errors:
        return templates.TemplateResponse(
            request,
            "account.html",
            _account_context(request, user, errors=errors, success=False),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Persist.
    users.set_password(user.email, new_password)
    access_log.log(
        action="password_changed",
        user_email=user.email,
        ip_address=client_ip(request),
        user_agent=client_ua(request),
    )

    # Session stays live — no sign_out/sign_in cycle needed.
    return templates.TemplateResponse(
        request,
        "account.html",
        _account_context(request, user, errors=[], success=True),
    )
