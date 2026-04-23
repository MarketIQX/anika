"""Append-only reasoning log.

Every agent call produces exactly one row. The table has a DB-level trigger
that blocks UPDATE and DELETE so this log is an immutable audit trail.
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any

from app.db import execute

logger = logging.getLogger(__name__)


def log(
    agent_name: str,
    input_obj: Any,
    output_obj: Any | None = None,
    reasoning_text: str | None = None,
    model: str | None = None,
    prompt_version: int | None = None,
    latency_ms: int | None = None,
    email_id: int | None = None,
    draft_id: int | None = None,
    status: str = "ok",
    error_text: str | None = None,
) -> int:
    """Persist a single reasoning-log row. Returns the row id."""
    cur = execute(
        """
        INSERT INTO reasoning_log
          (agent_name, email_id, draft_id, input_json, output_json,
           reasoning_text, model, prompt_version, latency_ms, status, error_text)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            agent_name,
            email_id,
            draft_id,
            json.dumps(input_obj, ensure_ascii=False, default=str),
            json.dumps(output_obj, ensure_ascii=False, default=str) if output_obj is not None else None,
            reasoning_text,
            model,
            prompt_version,
            latency_ms,
            status,
            error_text,
        ),
    )
    return int(cur.lastrowid)


@contextmanager
def timed(
    agent_name: str,
    input_obj: Any,
    email_id: int | None = None,
    draft_id: int | None = None,
    model: str | None = None,
    prompt_version: int | None = None,
):
    """Context manager that times a block and logs success OR failure.

    Usage:
        with timed('classifier', {'email_id': 42}) as ctx:
            result = run_classifier(...)
            ctx['output'] = result
            ctx['reasoning'] = result.get('reasoning')
    """
    ctx: dict[str, Any] = {
        "output": None,
        "reasoning": None,
        "model": model,
        "prompt_version": prompt_version,
    }
    start = time.perf_counter()
    try:
        yield ctx
    except Exception as e:
        elapsed = int((time.perf_counter() - start) * 1000)
        log(
            agent_name=agent_name,
            input_obj=input_obj,
            output_obj=None,
            reasoning_text=None,
            model=ctx.get("model"),
            prompt_version=ctx.get("prompt_version"),
            latency_ms=elapsed,
            email_id=email_id,
            draft_id=draft_id,
            status="error",
            error_text=str(e),
        )
        raise
    else:
        elapsed = int((time.perf_counter() - start) * 1000)
        log(
            agent_name=agent_name,
            input_obj=input_obj,
            output_obj=ctx.get("output"),
            reasoning_text=ctx.get("reasoning"),
            model=ctx.get("model"),
            prompt_version=ctx.get("prompt_version"),
            latency_ms=elapsed,
            email_id=email_id,
            draft_id=draft_id,
            status="ok",
        )
