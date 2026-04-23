"""FastAPI entrypoint — mounts dashboard, auth, runs startup jobs.

Startup sequence:
  1. init_db() — schema + triggers + vec table.
  2. backfill_memory.run() — seed firm_knowledge / rules / prompts.
  3. bootstrap.seed_initial_users() — seed AK + Prakash sir on first boot.
  4. Start Gmail polling background task.

Middleware stack (outermost first):
  - SecurityHeadersMiddleware
  - SessionMiddleware (itsdangerous-signed cookies)
  - FastAPI router tree
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import bootstrap as auth_bootstrap
from app.auth.middleware import SecurityHeadersMiddleware
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.dashboard.routes import router as dashboard_router
from app.db import init_db
from app.jobs import backfill_memory, poll_gmail

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    settings = get_settings()

    init_db()
    try:
        backfill_memory.run(seed_memory_vectors=False)
    except Exception as e:  # noqa: BLE001
        logger.exception("backfill_memory failed at startup: %s", e)

    # Seed the two default users on first boot only.
    try:
        auth_bootstrap.seed_initial_users()
    except Exception as e:  # noqa: BLE001
        logger.exception("user seed failed: %s", e)

    poll_gmail.start()
    logger.info(
        "Anika ready. Dashboard at http://%s:%s  |  Test mode: %s",
        settings.anika_host, settings.anika_port, settings.anika_test_mode,
    )
    try:
        yield
    finally:
        await poll_gmail.stop()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Anika", version="1.0.0", lifespan=lifespan)

    # Session cookie — signed with itsdangerous, lives on the client.
    # https_only tracks SESSION_COOKIE_SECURE; set true behind TLS.
    app.add_middleware(
        SessionMiddleware,
        secret_key=s.session_secret,
        max_age=60 * 60 * 24 * max(s.session_max_age_days, 1),
        same_site="lax",
        https_only=s.session_cookie_secure,
        session_cookie="anika_session",
    )
    # Security headers wrap everything (added last so it's outermost).
    app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=s.session_cookie_secure)

    # Auth routes first (they are public).
    app.include_router(auth_router)
    app.include_router(dashboard_router)

    from pathlib import Path
    static_dir = Path(__file__).parent / "dashboard" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.anika_host,
        port=s.anika_port,
        reload=False,
        log_level="info",
    )
