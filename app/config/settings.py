"""Anika configuration loader.

Loads environment variables from `.env` into a Pydantic settings model.
Single source of truth for all runtime configuration — no other module
should read os.environ directly.

Why pydantic-settings: gives us typed validation + defaults in one place.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# app/config/settings.py   → .parent = app/config/   → .parent.parent = app/
# → .parent.parent.parent = project root. (This file used to live at
# app/config.py so the old code only needed two .parents.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Anika runtime settings sourced from `.env`.

    All fields mirror the keys in `.env.example`. Defaults are chosen to be
    safe for a first-boot laptop deployment.
    """

    # Gmail OAuth
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    prakasha_email: str = Field(default="prakasha@balakrishnaandco.com")
    approval_notify_email: str = Field(default="")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model_drafter: str = Field(default="gpt-4o")
    openai_model_classifier: str = Field(default="gpt-4o-mini")
    openai_model_enricher: str = Field(default="gpt-4o-mini")
    openai_model_learner: str = Field(default="gpt-4o-mini")
    openai_model_embedding: str = Field(default="text-embedding-3-small")

    # App
    anika_public_base_url: str = Field(default="http://localhost:8000")
    anika_host: str = Field(default="127.0.0.1")
    anika_port: int = Field(default=8000)

    gmail_poll_interval_seconds: int = Field(default=30)
    daily_send_cap: int = Field(default=30)
    undo_window_seconds: int = Field(default=10)

    anika_test_mode: bool = Field(default=False)
    anika_tz: str = Field(default="Asia/Kolkata")

    # Auth — session cookie signing + first-boot user seed.
    # Why a separate secret: we never want .env leakage to unlock existing sessions.
    # Rotate this (and restart) to invalidate every session at once.
    session_secret: str = Field(default="change-me-in-production-please")
    session_max_age_days: int = Field(default=7)
    # If True, the session cookie has the Secure flag (HTTPS only). Set to False
    # during localhost pilot; flip to True once Cloudflare Tunnel/TLS is in place.
    session_cookie_secure: bool = Field(default=False)

    # First-boot seeding of the two default users. If empty, random passwords
    # are generated and printed once to the console.
    ak_email: str = Field(default="aks@marketiqx.com")
    ak_initial_password: str = Field(default="")
    prakasha_initial_password: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Paths — plain Python properties (not computed_field) so tests can subclass + override.
    # Why not pydantic fields: we don't want them settable from env; they're derived from the
    # project root, which is constant in production and needs to be redirectable in tests.

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        return PROJECT_ROOT / "anika.db"

    @property
    def token_path(self) -> Path:
        """Absolute path to the Gmail OAuth token JSON (created on first run)."""
        return PROJECT_ROOT / "token.json"

    @property
    def credentials_path(self) -> Path:
        """Path to an optional credentials.json (preferred by Google's installed-app flow)."""
        return PROJECT_ROOT / "credentials.json"

    @property
    def logs_dir(self) -> Path:
        """Directory for app-level log files."""
        d = PROJECT_ROOT / "data" / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def notify_email(self) -> str:
        """Where approval-ready notifications go. Defaults to prakasha_email."""
        return self.approval_notify_email.strip() or self.prakasha_email


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so that reading .env happens exactly once per process. Also exports
    OPENAI_API_KEY to os.environ so the OpenAI Agents SDK's default
    AsyncOpenAI() constructor — which reads only from the environment — can
    instantiate itself without our help.
    """
    s = Settings()
    if s.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = s.openai_api_key
    return s
