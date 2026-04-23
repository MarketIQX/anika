"""Memory Core tool — embed + store + semantic retrieve.

Built on sqlite-vec. Every memory row has a companion vector in memory_vec.
Retrieval is cosine similarity via the vec0 virtual table.

Why sqlite-vec: real semantic search (not keyword matching) and it ships
Windows wheels — unlike sqlite-vss, which the architecture doc originally
specified but has no Windows build. Semantics are identical (cosine over
float32 vectors of the configured embedding dim).
"""
from __future__ import annotations

import json
import logging
import struct
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.db import EMBEDDING_DIM, execute, fetch_all, fetch_one, get_conn

logger = logging.getLogger(__name__)


def _client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)


def _pack_vector(vec: list[float]) -> bytes:
    """Pack a list[float] into the little-endian float32 bytes sqlite-vec expects."""
    if len(vec) != EMBEDDING_DIM:
        raise ValueError(
            f"Expected {EMBEDDING_DIM}-dim vector, got {len(vec)}"
        )
    return struct.pack(f"{EMBEDDING_DIM}f", *vec)


def embed(text: str) -> list[float]:
    """Call OpenAI's embedding model and return the vector.

    Returns an empty list on empty input (the caller should skip storage).
    Raises on API errors — caller decides whether to retry.
    """
    text = (text or "").strip()
    if not text:
        return []
    resp = _client().embeddings.create(
        model=get_settings().openai_model_embedding,
        input=text,
    )
    return list(resp.data[0].embedding)


def store_memory(
    kind: str,
    content: str,
    service_line: str | None = None,
    subject: str | None = None,
    source_email_id: int | None = None,
    source_draft_id: int | None = None,
    tags: list[str] | None = None,
) -> int | None:
    """Persist a memory row + its embedding. Returns the memory.id or None.

    If `content` is empty or the embedding call fails, nothing is written and
    None is returned — Anika must still function without memory.
    """
    content = (content or "").strip()
    if not content:
        return None
    try:
        vec = embed(content)
    except Exception as e:  # noqa: BLE001 — degrade gracefully; log and skip
        logger.error("Embedding failed, skipping memory store: %s", e)
        return None
    if not vec:
        return None

    model = get_settings().openai_model_embedding
    cur = execute(
        """
        INSERT INTO memory(kind, service_line, subject, content,
                           source_email_id, source_draft_id, tags, embedding_model)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            kind,
            service_line,
            subject,
            content,
            source_email_id,
            source_draft_id,
            json.dumps(tags or [], ensure_ascii=False),
            model,
        ),
    )
    memory_id = int(cur.lastrowid)

    packed = _pack_vector(vec)
    execute(
        "INSERT INTO memory_vec(memory_id, embedding) VALUES (?, ?)",
        (memory_id, packed),
    )
    return memory_id


def semantic_search(
    query: str,
    top_k: int = 4,
    service_line: str | None = None,
    kinds: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return top_k most-similar memory rows for `query`.

    Args:
        query: natural-language retrieval query (usually the incoming email
            subject + first ~500 chars of body).
        top_k: number of neighbours to return.
        service_line: if set, post-filter to memories tagged with this line.
        kinds: if set, post-filter to these kinds.

    Returns:
        List of dicts with keys: id, kind, service_line, subject, content, distance.
    """
    query = (query or "").strip()
    if not query:
        return []
    try:
        qvec = embed(query)
    except Exception as e:  # noqa: BLE001
        logger.error("Embedding failed, returning no memories: %s", e)
        return []
    if not qvec:
        return []

    # vec0 syntax: MATCH + k parameter returns top-k by L2 distance.
    # We multiply top_k by 3 then post-filter so that filters don't starve results.
    raw_k = top_k * 3 if (service_line or kinds) else top_k
    packed = _pack_vector(qvec)

    rows = fetch_all(
        """
        SELECT v.memory_id AS id, v.distance AS distance,
               m.kind, m.service_line, m.subject, m.content, m.tags
        FROM memory_vec v
        JOIN memory m ON m.id = v.memory_id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
        """,
        (packed, raw_k),
    )

    def matches(row: dict[str, Any]) -> bool:
        if service_line and row.get("service_line") != service_line:
            return False
        if kinds and row.get("kind") not in kinds:
            return False
        return True

    filtered = [r for r in rows if matches(r)]
    return filtered[:top_k]


def delete_memory(memory_id: int) -> None:
    """Delete a memory row and its vector companion."""
    execute("DELETE FROM memory_vec WHERE memory_id = ?", (memory_id,))
    execute("DELETE FROM memory WHERE id = ?", (memory_id,))


def count_memories() -> int:
    row = fetch_one("SELECT COUNT(*) AS n FROM memory")
    return int(row["n"]) if row else 0
