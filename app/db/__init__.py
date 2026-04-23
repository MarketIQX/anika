"""Database package — SQLite connection, migrations, and helpers."""
from app.db.connection import (
    connect,
    init_db,
    get_conn,
    execute,
    fetch_one,
    fetch_all,
    EMBEDDING_DIM,
)

__all__ = [
    "connect",
    "init_db",
    "get_conn",
    "execute",
    "fetch_one",
    "fetch_all",
    "EMBEDDING_DIM",
]
