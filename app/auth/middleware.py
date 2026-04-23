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
