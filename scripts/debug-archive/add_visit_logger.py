from pathlib import Path

# ============================================================
# Patch 1 — Add PageVisitLoggerMiddleware to app/auth/middleware.py
# ============================================================
p = Path("app/auth/middleware.py")
code = p.read_text(encoding="utf-8")

if "PageVisitLoggerMiddleware" in code:
    print("PageVisitLoggerMiddleware already exists — skipping append")
else:
    new_middleware = '''


# ---------------------------------------------------------------------
# Page-visit logger (Phase 1B+)
# ---------------------------------------------------------------------

# Paths to skip (high-frequency / low-value)
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

    Why: action-only logging (POSTs) misses the user's exploration pattern
    (which tabs they viewed, which drafts they opened). This gives us a
    complete navigation timeline per partner.

    Skips: login/logout (no user yet), favicon, static assets, non-GET
    methods (POSTs are already logged via access_log.log() in route handlers).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Pass-through: only log GETs we care about
        should_log = (
            request.method == "GET"
            and request.url.path not in _SKIP_PATHS_EXACT
            and not any(request.url.path.startswith(p) for p in _SKIP_PREFIXES)
        )

        response = await call_next(request)

        if should_log:
            # Resolve user from session — same pattern as auth middleware uses
            try:
                user_email = request.session.get("user_email") if hasattr(request, "session") else None
                if user_email:
                    # Lazy import to avoid circulars at module load time
                    from app.auth import access_log
                    access_log.log(
                        action="page_visit",
                        user_email=user_email,
                        target=request.url.path,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                    )
            except Exception:
                # Never let logging break the response
                pass

        return response
'''
    code = code.rstrip() + new_middleware
    p.write_text(code, encoding="utf-8")
    print("Added PageVisitLoggerMiddleware to app/auth/middleware.py")

# Verify import
import sys
for mod in list(sys.modules):
    if "auth.middleware" in mod or "app.auth" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app.auth.middleware import PageVisitLoggerMiddleware, SecurityHeadersMiddleware
    print("Both middleware classes import cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")


# ============================================================
# Patch 2 — Register PageVisitLoggerMiddleware in main.py
# ============================================================
p2 = Path("app/main.py")
code2 = p2.read_text(encoding="utf-8")

# Update import line
OLD_IMPORT = "from app.auth.middleware import SecurityHeadersMiddleware"
NEW_IMPORT = "from app.auth.middleware import PageVisitLoggerMiddleware, SecurityHeadersMiddleware"
if OLD_IMPORT in code2 and NEW_IMPORT not in code2:
    code2 = code2.replace(OLD_IMPORT, NEW_IMPORT)
    print("Updated import in main.py")

# Register the middleware. Order matters in FastAPI:
# add_middleware adds to the OUTSIDE of the stack.
# We want PageVisitLogger to run AFTER session middleware (so request.session exists)
# but BEFORE security headers (innermost). FastAPI processes them in reverse.
# Best position: right after SessionMiddleware add line.
OLD_REG = "app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=s.session_cookie_secure)"
NEW_REG = """app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=s.session_cookie_secure)
    app.add_middleware(PageVisitLoggerMiddleware)"""

if "PageVisitLoggerMiddleware)" in code2:
    print("PageVisitLoggerMiddleware already registered")
elif OLD_REG in code2:
    code2 = code2.replace(OLD_REG, NEW_REG)
    p2.write_text(code2, encoding="utf-8")
    print("Registered PageVisitLoggerMiddleware in main.py")
else:
    print("Could not find SecurityHeaders registration point")

# Verify final import
import sys
for mod in list(sys.modules):
    if "app.main" in mod or "app.auth" in mod:
        del sys.modules[mod]
sys.path.insert(0, ".")
try:
    from app import main as _m
    print()
    print("main.py imports cleanly")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
