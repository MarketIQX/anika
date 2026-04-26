from pathlib import Path

# ============================================================
# Add PageVisitLoggerMiddleware to app/auth/middleware.py
# ============================================================
p = Path("app/auth/middleware.py")
code = p.read_text(encoding="utf-8")

if "PageVisitLoggerMiddleware" in code:
    print("PageVisitLoggerMiddleware already exists")
else:
    new_middleware = '''


# ---------------------------------------------------------------------
# Page-visit logger (Phase 1B+)
# ---------------------------------------------------------------------

_SKIP_PATHS_EXACT = {
    "/favicon.ico",
    "/login",
    "/logout",
}
_SKIP_PREFIXES = (
    "/static/",
    "/_static/",
)


class PageVisitLoggerMiddleware(BaseHTTPMiddleware):
    """Log every authenticated GET request to access_log.

    Why: action-only logging (POSTs) misses navigation (which tabs viewed,
    which drafts opened). This gives full timeline per partner.

    Skips: login/logout (no user yet), favicon, static, non-GET (POSTs
    already logged via access_log.log() in route handlers).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        should_log = (
            request.method == "GET"
            and request.url.path not in _SKIP_PATHS_EXACT
            and not any(request.url.path.startswith(p) for p in _SKIP_PREFIXES)
        )

        response = await call_next(request)

        if should_log:
            try:
                user_email = request.session.get("user_email") if hasattr(request, "session") else None
                if user_email:
                    from app.auth import access_log
                    access_log.log(
                        action="page_visit",
                        user_email=user_email,
                        target=request.url.path,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                    )
            except Exception:
                pass

        return response
'''
    code = code.rstrip() + new_middleware
    p.write_text(code, encoding="utf-8")
    print("Added PageVisitLoggerMiddleware to app/auth/middleware.py")

# ============================================================
# Register in main.py
# ============================================================
p2 = Path("app/main.py")
code2 = p2.read_text(encoding="utf-8")

OLD_IMPORT = "from app.auth.middleware import SecurityHeadersMiddleware"
NEW_IMPORT = "from app.auth.middleware import PageVisitLoggerMiddleware, SecurityHeadersMiddleware"
if NEW_IMPORT in code2:
    print("Import already updated")
elif OLD_IMPORT in code2:
    code2 = code2.replace(OLD_IMPORT, NEW_IMPORT)
    print("Updated import in main.py")

OLD_REG = "app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=s.session_cookie_secure)"
NEW_REG = """app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=s.session_cookie_secure)
    app.add_middleware(PageVisitLoggerMiddleware)"""

if "PageVisitLoggerMiddleware)" in code2 and "app.add_middleware(PageVisitLoggerMiddleware)" in code2:
    print("PageVisitLoggerMiddleware already registered")
elif OLD_REG in code2:
    code2 = code2.replace(OLD_REG, NEW_REG)
    print("Registered PageVisitLoggerMiddleware in main.py")

p2.write_text(code2, encoding="utf-8")

# Verify
import sys
for mod in list(sys.modules):
    if "app.main" in mod or "app.auth" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app import main as _m
    from app.auth.middleware import PageVisitLoggerMiddleware, SecurityHeadersMiddleware
    print()
    print("All imports clean")
    print(f"PageVisitLoggerMiddleware: {PageVisitLoggerMiddleware is not None}")
    print(f"SecurityHeadersMiddleware: {SecurityHeadersMiddleware is not None}")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
