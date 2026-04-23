"""Pytest fixtures.

Every test uses a fresh SQLite file under tmp_path so tests don't stomp the
real anika.db. We override the path by patching every module that imported
`get_settings` via `from app.config import get_settings` (Python's
from-import creates per-module bindings that each need redirecting).
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


# Modules that do `from app.config import get_settings` — each needs the patched reference.
_MODULES_USING_GET_SETTINGS = [
    "app.config",
    "app.db.connection",
    "app.tools.gmail_tool",
    "app.tools.memory_tool",
    "app.tools.notify_tool",
    "app.guardrails.daily_cap",
    "app.agents.classifier",
    "app.agents.enricher",
    "app.agents.drafter",
    "app.agents.sender",
    "app.agents.orchestrator",
    "app.cognitive.learning_engine",
    "app.jobs.poll_gmail",
    "app.main",
    "app.dashboard.routes",
    "app.auth.bootstrap",
]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Force every test to use a fresh db in tmp_path."""
    import app.db.connection as conn_mod
    from app import config as config_mod

    db_file = tmp_path / "test_anika.db"

    # Subclass Settings so tests can redirect path-valued @properties.
    class _TestSettings(config_mod.Settings):
        @property
        def db_path(self) -> Path:
            return db_file

        @property
        def token_path(self) -> Path:
            return tmp_path / "token.json"

        @property
        def credentials_path(self) -> Path:
            return tmp_path / "credentials.json"

        @property
        def logs_dir(self) -> Path:
            d = tmp_path / "logs"
            d.mkdir(parents=True, exist_ok=True)
            return d

        @property
        def notify_email(self) -> str:
            return self.approval_notify_email.strip() or self.prakasha_email

    test_settings = _TestSettings(openai_api_key="test-key-not-used")
    fake_get = lambda: test_settings  # noqa: E731

    # Clear the real lru_cache BEFORE replacing it — after replacement, the
    # attribute is a plain lambda without .cache_clear().
    config_mod.get_settings.cache_clear()

    # Patch get_settings everywhere it has been `from`-imported.
    for mod_name in _MODULES_USING_GET_SETTINGS:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "get_settings"):
            monkeypatch.setattr(mod, "get_settings", fake_get)

    # Drop any stale shared connection pointing at the real anika.db.
    if conn_mod._SHARED_CONN is not None:
        try:
            conn_mod._SHARED_CONN.close()
        except Exception:
            pass
    monkeypatch.setattr(conn_mod, "_SHARED_CONN", None, raising=False)

    # Initialize the fresh db.
    from app.db import init_db

    init_db()

    yield

    if conn_mod._SHARED_CONN is not None:
        try:
            conn_mod._SHARED_CONN.close()
        except Exception:
            pass
        conn_mod._SHARED_CONN = None
