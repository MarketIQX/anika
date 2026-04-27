"""Phase 1C-1 — self-measurement.

When a draft chain reaches a terminal state (sent or rejected),
compute_journey_metric() walks the chain from root to tip, computes
the edit-distance from Anika's first attempt to the final draft, and
persists a draft_metrics row.

The metric isolates ONE thing: how much human-correction did Anika need
before the partner approved (or gave up on) this email? Lower is better.
Tracked over time per service_line, this is the most direct measure of
adaptation we can extract from the existing pipeline without
instrumenting the LLM itself.

Design choices:
  - "Journey" is keyed by email_id. One terminal state per email-journey.
  - Root draft = the one with parent_draft_id IS NULL for that email_id.
    Phase 1B's draft chain links each new draft to its predecessor via
    parent_draft_id when an edit happens.
  - Final draft = the draft whose status is now 'sent' (for outcome=sent)
    or the draft whose status is 'rejected' (for outcome=rejected).
  - Edit distance = 1.0 - SequenceMatcher(first.body, final.body).ratio().
    0.0 = identical (no human correction). 1.0 = complete rewrite.
  - cognitive_state + voice_coverage_count are snapshotted from the FIRST
    draft so trends stay comparable when the same service line transitions
    cold_start → learning → learned mid-history.

Best-effort: every helper is wrapped to never raise into the calling
pipeline. A metric failure must not block a send or a rejection.
"""
from __future__ import annotations

import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Literal

from app.db import execute, fetch_all, fetch_one

logger = logging.getLogger(__name__)


Outcome = Literal["sent", "rejected"]


# ---------------------------------------------------------------------------
# Journey traversal
# ---------------------------------------------------------------------------


def _root_draft_for_email(email_id: int) -> dict[str, Any] | None:
    """Return the first draft for this email (the one with no parent)."""
    return fetch_one(
        """
        SELECT id, body, cognitive_state, voice_coverage_count, created_at
          FROM drafts
         WHERE email_id = ? AND parent_draft_id IS NULL
         ORDER BY id ASC LIMIT 1
        """,
        (email_id,),
    )


def _final_draft_for_outcome(email_id: int, outcome: Outcome) -> dict[str, Any] | None:
    """Return the draft that reached the terminal state, or None.

    For 'sent': the draft with sent_status='sent' (there should be exactly one).
    For 'rejected': the draft with sent_status='rejected'. If multiple exist
    (rare, but possible if an edit chain ended in another rejection), we
    take the most recent.
    """
    target_status = "sent" if outcome == "sent" else "rejected"
    return fetch_one(
        """
        SELECT id, body, created_at, updated_at
          FROM drafts
         WHERE email_id = ? AND sent_status = ?
         ORDER BY id DESC LIMIT 1
        """,
        (email_id, target_status),
    )


def _chain_length(email_id: int) -> int:
    """How many draft rows belong to this email_id (any status)."""
    row = fetch_one("SELECT COUNT(*) AS n FROM drafts WHERE email_id = ?", (email_id,))
    return int(row["n"]) if row else 0


def _service_line_for_email(email_id: int) -> str | None:
    row = fetch_one(
        "SELECT likely_service_line FROM enrichments "
        "WHERE email_id = ? ORDER BY id DESC LIMIT 1",
        (email_id,),
    )
    return row["likely_service_line"] if row else None


# ---------------------------------------------------------------------------
# Edit-distance + duration
# ---------------------------------------------------------------------------


def _edit_distance(a: str, b: str) -> tuple[float, float]:
    """Return (edit_distance, similarity_ratio).

    Wraps difflib.SequenceMatcher.ratio() — same algorithm
    learning_engine.compute_delta() uses, kept consistent so the two
    surfaces report comparable numbers.
    """
    if not a and not b:
        return 0.0, 1.0
    sm = SequenceMatcher(None, a or "", b or "")
    sim = sm.ratio()
    return round(1.0 - sim, 4), round(sim, 4)


def _duration_seconds(start_iso: str | None, end_iso: str | None) -> int | None:
    """ISO-8601 → seconds elapsed. Returns None if either timestamp is missing/malformed."""
    if not start_iso or not end_iso:
        return None
    try:
        # SQLite's strftime('%Y-%m-%dT%H:%M:%fZ', 'now') gives
        # microsecond-precision UTC. fromisoformat handles that on 3.11+
        # if we strip the trailing Z first.
        s = datetime.fromisoformat(start_iso.rstrip("Z"))
        e = datetime.fromisoformat(end_iso.rstrip("Z"))
    except ValueError:
        return None
    return max(int((e - s).total_seconds()), 0)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_journey_metric(email_id: int, *, outcome: Outcome) -> int | None:
    """Compute and persist the journey metric for `email_id`. Returns the
    new draft_metrics.id, or None if the metric couldn't be computed.

    Idempotent: if a metric row already exists for this (email_id, outcome),
    we skip and return the existing id. This protects against double-counting
    if approver fires twice or if the pipeline retries.
    """
    try:
        existing = fetch_one(
            "SELECT id FROM draft_metrics WHERE email_id = ? AND final_outcome = ?",
            (email_id, outcome),
        )
        if existing:
            return int(existing["id"])

        first = _root_draft_for_email(email_id)
        final = _final_draft_for_outcome(email_id, outcome)
        if not first or not final:
            logger.info(
                "compute_journey_metric skipped: email_id=%s outcome=%s "
                "first=%s final=%s",
                email_id, outcome, bool(first), bool(final),
            )
            return None

        edit_dist, sim = _edit_distance(first["body"] or "", final["body"] or "")
        chain_len = _chain_length(email_id)
        service_line = _service_line_for_email(email_id)
        duration = _duration_seconds(
            first.get("created_at"), final.get("updated_at") or final.get("created_at")
        )

        cur = execute(
            """
            INSERT INTO draft_metrics
              (email_id, first_draft_id, final_draft_id, final_outcome,
               service_line, cognitive_state, voice_coverage_count,
               chain_length, edit_distance, similarity_ratio, duration_seconds)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                email_id,
                int(first["id"]),
                int(final["id"]),
                outcome,
                service_line,
                first.get("cognitive_state"),
                first.get("voice_coverage_count"),
                chain_len,
                edit_dist,
                sim,
                duration,
            ),
        )
        metric_id = int(cur.lastrowid)
        logger.info(
            "draft_metrics: email_id=%s outcome=%s service=%s "
            "chain_len=%s edit_dist=%.4f similarity=%.4f duration=%ss → id=%s",
            email_id, outcome, service_line, chain_len, edit_dist, sim,
            duration, metric_id,
        )
        return metric_id
    except Exception as e:  # noqa: BLE001 — never let a metric failure block sending
        logger.exception(
            "compute_journey_metric failed for email_id=%s outcome=%s: %s",
            email_id, outcome, e,
        )
        return None


# ---------------------------------------------------------------------------
# Read-side helpers — used by the /train/learning-curves panel.
# ---------------------------------------------------------------------------


def per_service_line_summary() -> list[dict[str, Any]]:
    """Aggregate metrics per service_line for the dashboard panel.

    Returns a list of dicts:
      [{
         service_line,
         total_count,                  -- total journeys in this line
         sent_count, rejected_count,
         mean_edit_distance,           -- across SENT only (rejected dilutes)
         recent5_distances,            -- [d1, d2, ...] up to 5, oldest→newest
         recent5_mean,
         all_time_mean,
         trend,                        -- 'improving' | 'stable' | 'regressing' | 'insufficient_data'
         cold_start_count, learning_count, learned_count,
       }]
    """
    out: list[dict[str, Any]] = []
    rows = fetch_all(
        "SELECT DISTINCT service_line FROM draft_metrics ORDER BY service_line"
    )
    for r in rows:
        sl = r["service_line"]
        sl_label = "(none)" if sl is None else sl

        total = fetch_one(
            "SELECT COUNT(*) AS n FROM draft_metrics WHERE service_line IS ?",
            (sl,),
        )["n"]
        sent_n = fetch_one(
            "SELECT COUNT(*) AS n FROM draft_metrics "
            "WHERE service_line IS ? AND final_outcome='sent'",
            (sl,),
        )["n"]
        rej_n = fetch_one(
            "SELECT COUNT(*) AS n FROM draft_metrics "
            "WHERE service_line IS ? AND final_outcome='rejected'",
            (sl,),
        )["n"]

        # Edit-distance trend — SENT only (rejected ones aren't "learning")
        sent_metrics = fetch_all(
            """
            SELECT id, edit_distance, cognitive_state, created_at
              FROM draft_metrics
             WHERE service_line IS ? AND final_outcome='sent'
             ORDER BY id ASC
            """,
            (sl,),
        )
        all_dists = [m["edit_distance"] for m in sent_metrics if m["edit_distance"] is not None]
        all_mean = round(sum(all_dists) / len(all_dists), 4) if all_dists else None

        recent5 = sent_metrics[-5:]
        recent5_dists = [m["edit_distance"] for m in recent5 if m["edit_distance"] is not None]
        recent5_mean = round(sum(recent5_dists) / len(recent5_dists), 4) if recent5_dists else None

        trend = "insufficient_data"
        if all_mean is not None and recent5_mean is not None and len(all_dists) >= 3:
            # Compare recent-5 mean against all-time mean of EARLIER drafts.
            earlier = all_dists[:-5] if len(all_dists) > 5 else []
            earlier_mean = round(sum(earlier) / len(earlier), 4) if earlier else None
            if earlier_mean is None:
                trend = "insufficient_data"
            elif recent5_mean < earlier_mean - 0.03:
                trend = "improving"
            elif recent5_mean > earlier_mean + 0.03:
                trend = "regressing"
            else:
                trend = "stable"

        cog_dist = {"cold_start": 0, "learning": 0, "learned": 0, None: 0}
        for m in sent_metrics:
            cog_dist[m["cognitive_state"]] = cog_dist.get(m["cognitive_state"], 0) + 1

        out.append({
            "service_line": sl_label,
            "service_line_raw": sl,
            "total_count": total,
            "sent_count": sent_n,
            "rejected_count": rej_n,
            "mean_edit_distance": all_mean,
            "recent5_distances": recent5_dists,
            "recent5_mean": recent5_mean,
            "all_time_mean": all_mean,
            "trend": trend,
            "cold_start_count": cog_dist.get("cold_start", 0),
            "learning_count": cog_dist.get("learning", 0),
            "learned_count": cog_dist.get("learned", 0),
        })
    return out


def recent_metrics(limit: int = 30) -> list[dict[str, Any]]:
    """Most recent metrics across all service lines, for the dashboard timeline."""
    return fetch_all(
        """
        SELECT m.id, m.email_id, m.service_line, m.cognitive_state,
               m.chain_length, m.edit_distance, m.final_outcome,
               m.duration_seconds, m.created_at,
               r.from_email, r.subject
          FROM draft_metrics m
          LEFT JOIN raw_emails r ON r.id = m.email_id
         ORDER BY m.id DESC LIMIT ?
        """,
        (limit,),
    )
