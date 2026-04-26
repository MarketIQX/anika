"""Knowledge-library retrieval, write path, and usage counters.

The Drafter reads from here at prompt-assembly time:
  retrieve_rules(service_line)     → universal + service-line rules/policies
  retrieve_examples(service_line)  → top-k semantically similar examples
  retrieve_facts(service_line)     → universal + service-line facts

Writes happen via `add_entry()` (embed + vec insert + knowledge_library insert)
and `soft_delete_entry()` (flip is_active=0, audit).
"""
from __future__ import annotations

import json
import logging
import struct
from typing import Any

from app.db import EMBEDDING_DIM, execute, fetch_all, fetch_one
from app.tools import memory_tool

logger = logging.getLogger(__name__)


def _pack_vector(vec: list[float]) -> bytes:
    if len(vec) != EMBEDDING_DIM:
        raise ValueError(f"expected {EMBEDDING_DIM}-dim vector, got {len(vec)}")
    return struct.pack(f"{EMBEDDING_DIM}f", *vec)


# --------------------------------------------------------------------------
# Write path
# --------------------------------------------------------------------------


def add_entry(
    *,
    kind: str,
    content: str,
    service_line: str | None = None,
    scope: str = "universal",
    source_queue_id: int | None = None,
    confidence: float = 1.0,
    created_by: str | None = None,
) -> int | None:
    """Insert a knowledge_library row + its embedding. Returns library.id.

    Returns None if content is empty or embedding fails (we don't want a
    row that can never be retrieved).
    """
    content = (content or "").strip()
    if not content:
        return None
    try:
        vec = memory_tool.embed(content)
    except Exception as e:  # noqa: BLE001
        logger.error("library embed failed, skipping add_entry: %s", e)
        return None
    if not vec:
        return None
    cur = execute(
        """
        INSERT INTO knowledge_library
          (kind, content, service_line, scope, source_queue_id, confidence, created_by)
        VALUES (?,?,?,?,?,?,?)
        """,
        (kind, content, service_line, scope, source_queue_id, float(confidence), created_by),
    )
    library_id = int(cur.lastrowid)
    execute(
        "INSERT INTO knowledge_library_vec(library_id, embedding) VALUES (?, ?)",
        (library_id, _pack_vector(vec)),
    )
    return library_id


def update_entry(library_id: int, *, content: str | None = None,
                 kind: str | None = None, scope: str | None = None,
                 service_line: str | None = None) -> bool:
    """Edit an existing library row (and re-embed if content changed)."""
    row = fetch_one("SELECT content FROM knowledge_library WHERE id=?", (library_id,))
    if not row:
        return False
    # Build dynamic update.
    sets: list[str] = []
    params: list[Any] = []
    new_content = content if content is not None else row["content"]
    if content is not None:
        sets.append("content=?"); params.append(content)
    if kind is not None:
        sets.append("kind=?"); params.append(kind)
    if scope is not None:
        sets.append("scope=?"); params.append(scope)
    if service_line is not None:
        sets.append("service_line=?"); params.append(service_line)
    if not sets:
        return False
    params.append(library_id)
    execute(
        f"UPDATE knowledge_library SET {', '.join(sets)} WHERE id=?",
        tuple(params),
    )
    # Re-embed if content changed.
    if content is not None:
        try:
            vec = memory_tool.embed(new_content)
        except Exception as e:  # noqa: BLE001
            logger.error("re-embed failed for library %s: %s", library_id, e)
            return True
        if vec:
            execute("DELETE FROM knowledge_library_vec WHERE library_id=?", (library_id,))
            execute(
                "INSERT INTO knowledge_library_vec(library_id, embedding) VALUES (?,?)",
                (library_id, _pack_vector(vec)),
            )
    return True


def soft_delete_entry(library_id: int, *, deleted_by: str | None = None) -> bool:
    """Set is_active=0 — never remove the row. Audit who + when."""
    row = fetch_one("SELECT id FROM knowledge_library WHERE id=? AND is_active=1",
                    (library_id,))
    if not row:
        return False
    execute(
        """
        UPDATE knowledge_library
           SET is_active = 0,
               deleted_by = ?,
               deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE id = ?
        """,
        (deleted_by, library_id),
    )
    return True


# --------------------------------------------------------------------------
# Retrieval — the Drafter's read path.
# --------------------------------------------------------------------------


def retrieve_rules(service_line: str | None) -> list[dict[str, Any]]:
    """Return active rule/policy rows relevant to the service_line.

    Rules with scope='universal' always apply; scope='service_line' rows
    only apply when their service_line matches.
    """
    if service_line:
        rows = fetch_all(
            """
            SELECT id, kind, content, service_line, scope
              FROM knowledge_library
             WHERE is_active = 1
               AND kind IN ('rule','policy')
               AND purpose IN ('voice_example','firm_policy','firm_fact','question_template','workflow_rule')
               AND (scope = 'universal' OR service_line = ?)
             ORDER BY scope ASC, id ASC
            """,
            (service_line,),
        )
    else:
        rows = fetch_all(
            """
            SELECT id, kind, content, service_line, scope
              FROM knowledge_library
             WHERE is_active = 1 AND kind IN ('rule','policy') AND purpose IN ('voice_example','firm_policy','firm_fact','question_template','workflow_rule') AND scope='universal'
             ORDER BY id ASC
            """
        )
    return rows


def retrieve_facts(service_line: str | None) -> list[dict[str, Any]]:
    if service_line:
        return fetch_all(
            """
            SELECT id, content, service_line, scope
              FROM knowledge_library
             WHERE is_active = 1 AND kind = 'fact'
               AND purpose IN ('voice_example','firm_policy','firm_fact','question_template','workflow_rule')
               AND (scope = 'universal' OR service_line = ?)
             ORDER BY scope, id
            """,
            (service_line,),
        )
    return fetch_all(
        """
        SELECT id, content, service_line, scope
          FROM knowledge_library
         WHERE is_active = 1 AND kind = 'fact' AND purpose IN ('voice_example','firm_policy','firm_fact','question_template','workflow_rule') AND scope = 'universal'
         ORDER BY id
        """
    )


def retrieve_examples(
    query_text: str,
    service_line: str | None,
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Return top-k semantically similar examples for the given query.

    Prefers examples with matching service_line, then falls back to any
    example if service-line-filtered results are thin.
    """
    try:
        qvec = memory_tool.embed(query_text)
    except Exception as e:  # noqa: BLE001
        logger.error("library example embed failed: %s", e)
        return []
    if not qvec:
        return []
    packed = _pack_vector(qvec)

    # Over-fetch then filter by kind='example' and is_active=1.
    raw_k = top_k * 4
    rows = fetch_all(
        """
        SELECT v.library_id AS id, v.distance AS distance,
               k.kind, k.content, k.service_line, k.scope
          FROM knowledge_library_vec v
          JOIN knowledge_library k ON k.id = v.library_id
         WHERE v.embedding MATCH ? AND k = ?
           AND k.is_active = 1 AND k.kind = 'example' AND k.purpose IN ('voice_example','firm_policy','firm_fact','question_template','workflow_rule')
         ORDER BY v.distance
        """,
        (packed, raw_k),
    )
    if service_line:
        prefer = [r for r in rows if r.get("service_line") == service_line]
        other = [r for r in rows if r.get("service_line") != service_line]
        rows = (prefer + other)[:top_k]
    else:
        rows = rows[:top_k]
    return rows


# --------------------------------------------------------------------------
# Usage counter
# --------------------------------------------------------------------------


def bump_applied(library_ids: list[int]) -> None:
    """Increment applied_count + stamp last_used_at on every row we touched."""
    if not library_ids:
        return
    # Parameterize a varying-length IN (...) clause.
    placeholders = ",".join("?" for _ in library_ids)
    execute(
        f"""
        UPDATE knowledge_library
           SET applied_count = applied_count + 1,
               last_used_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
         WHERE id IN ({placeholders}) AND is_active = 1
        """,
        tuple(library_ids),
    )


# --------------------------------------------------------------------------
# Admin introspection helpers
# --------------------------------------------------------------------------


def list_entries(
    *,
    kind: str | None = None,
    service_line: str | None = None,
    include_inactive: bool = False,
    limit: int = 500,
) -> list[dict[str, Any]]:
    where = []
    params: list[Any] = []
    if not include_inactive:
        where.append("is_active = 1")
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if service_line:
        where.append("(service_line = ? OR scope = 'universal')")
        params.append(service_line)
    sql = "SELECT * FROM knowledge_library"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    return fetch_all(sql, tuple(params))


def get_entry(library_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM knowledge_library WHERE id=?", (library_id,))


# --------------------------------------------------------------------------
# Cognitive state helpers (Phase 1B+)
# --------------------------------------------------------------------------

def voice_coverage(service_line: str | None) -> dict[str, Any]:
    """How much learned voice does Anika have for this service_line?

    Returns dict with:
      - count: number of voice_example entries
      - cognitive_state: 'cold_start' (0), 'learning' (1-2), 'learned' (3+)
      - service_line: the queried service_line
      - has_universal: whether universal-scope voice_examples exist as fallback
    """
    if service_line:
        sl_rows = fetch_all("""
            SELECT COUNT(*) n FROM knowledge_library
             WHERE is_active = 1
               AND purpose = 'voice_example'
               AND service_line = ?
        """, (service_line,))
    else:
        sl_rows = fetch_all("""
            SELECT COUNT(*) n FROM knowledge_library
             WHERE is_active = 1
               AND purpose = 'voice_example'
               AND (service_line IS NULL OR scope = 'universal')
        """)

    sl_count = sl_rows[0]["n"] if sl_rows else 0

    universal_rows = fetch_all("""
        SELECT COUNT(*) n FROM knowledge_library
         WHERE is_active = 1
           AND purpose = 'voice_example'
           AND scope = 'universal'
    """)
    universal_count = universal_rows[0]["n"] if universal_rows else 0

    if sl_count == 0:
        state = "cold_start"
    elif sl_count < 3:
        state = "learning"
    else:
        state = "learned"

    return {
        "count": sl_count,
        "cognitive_state": state,
        "service_line": service_line,
        "has_universal": universal_count > 0,
    }
