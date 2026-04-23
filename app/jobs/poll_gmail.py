"""Gmail polling job — runs every N seconds as an asyncio background task.

Why polling (not Pub/Sub): Gmail Pub/Sub requires domain verification we
cannot do on a laptop. 30s polling is acceptable latency for an
approval-gated workflow.

Behavior:
  - list messages matching "is:unread -from:me category:primary"
  - for each new one, call orchestrator.handle(msg)
  - errors in a single message don't stop the loop; they log and continue.
"""
from __future__ import annotations

import asyncio
import logging

from app.agents import orchestrator
from app.config import get_settings
from app.db import fetch_one
from app.tools import gmail_tool

logger = logging.getLogger(__name__)

_TASK: asyncio.Task | None = None


async def _poll_once() -> int:
    """Fetch + process any new unread primary-inbox messages. Returns count processed."""
    if not gmail_tool.has_credentials():
        # Can't poll without OAuth — dashboard shows a banner to connect Gmail.
        return 0

    ids = gmail_tool.list_recent_message_ids(max_results=15)
    if not ids:
        return 0

    processed = 0
    for mid in ids:
        # Skip if we already ingested this message (poll overlap or reprocess).
        if fetch_one("SELECT id FROM raw_emails WHERE gmail_message_id=?", (mid,)):
            continue
        try:
            msg = gmail_tool.fetch_message(mid)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", mid, e)
            continue
        try:
            await orchestrator.handle(msg)
            processed += 1
        except Exception as e:  # noqa: BLE001
            logger.exception("orchestrator.handle failed on %s: %s", mid, e)
    return processed


async def _loop() -> None:
    interval = max(get_settings().gmail_poll_interval_seconds, 5)
    logger.info("Gmail poll loop starting (interval=%ss)", interval)
    while True:
        try:
            n = await _poll_once()
            if n:
                logger.info("Gmail poll processed %s new message(s)", n)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected error in poll loop: %s", e)
        await asyncio.sleep(interval)


def start() -> asyncio.Task:
    """Start (or return the existing) background poll task."""
    global _TASK
    if _TASK is None or _TASK.done():
        _TASK = asyncio.create_task(_loop(), name="anika-gmail-poll")
    return _TASK


async def stop() -> None:
    global _TASK
    if _TASK and not _TASK.done():
        _TASK.cancel()
        try:
            await _TASK
        except asyncio.CancelledError:
            pass
        _TASK = None


async def poll_now() -> int:
    """Run a single poll cycle on demand — used by the dashboard 'Poll now' button."""
    return await _poll_once()
