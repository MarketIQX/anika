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

    # Sync Gmail calls (googleapiclient is blocking) go through
    # asyncio.to_thread so the FastAPI event loop stays responsive during
    # the HTTP round-trip. Without this, every poll cycle would freeze
    # page handlers for ~300-500ms × N calls.
    ids = await asyncio.to_thread(gmail_tool.list_recent_message_ids, max_results=15)

    processed = 0
    for mid in ids or []:
        # Skip if we already ingested this message (poll overlap or reprocess).
        if fetch_one("SELECT id FROM raw_emails WHERE gmail_message_id=?", (mid,)):
            continue
        try:
            msg = await asyncio.to_thread(gmail_tool.fetch_message, mid)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to fetch %s: %s", mid, e)
            continue
        try:
            await orchestrator.handle(msg)
            processed += 1
        except Exception as e:  # noqa: BLE001
            logger.exception("orchestrator.handle failed on %s: %s", mid, e)

    # Phase 1C-3 — outbound harvester. Scan tracked threads for partner
    # Gmail-direct replies that bypassed Anika, harvest them as voice
    # examples. Best-effort: any failure is logged and the loop continues.
    try:
        from app.jobs.outbound_harvester import harvest_outbound_replies
        await harvest_outbound_replies()
    except Exception as e:  # noqa: BLE001
        logger.warning("outbound_harvester pass failed: %s", e)

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
