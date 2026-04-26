"""Security headers middleware.

Minimal, defensible defaults for a single-tenant dashboard loaded behind
Cloudflare Tunnel. CSP is intentionally loose because we use Tailwind from
a CDN; tighten once we ship local assets.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add baseline security headers to every response.

    Why these:
      - X-Content-Type-Options: blocks MIME-sniffing XSS in older browsers.
      - X-Frame-Options: clickjacking defence (matches CSP frame-ancestors).
      - Strict-Transport-Security: only sent once HTTPS is in play.
      - Referrer-Policy: don't leak dashboard URLs to third parties.
      - Content-Security-Policy: minimal whitelist (Tailwind CDN + self).
    """

    def __init__(self, app, *, hsts_enabled: bool = False):
        super().__init__(app)
        self.hsts_enabled = hsts_enabled

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", _CSP)
        if self.hsts_enabled:
            # 180 days, include subdomains.
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=15552000; includeSubDomains"
            )
        return response


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
