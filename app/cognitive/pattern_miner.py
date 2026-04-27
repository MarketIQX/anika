"""Phase 1C-2 — pattern recognition.

Substring-based mining over terminal draft journeys. When the partner
consistently REMOVES (or ADDS) the same 3-7 word phrase across multiple
edits in the same service line, that's a real pattern worth surfacing.

Why substring-only and not LLM-summarized:
  - Deterministic and free.
  - Auditable — the partner can see the exact text that triggered the
    observation, no model interpretation in the loop.
  - Defensible to ICAI: "the system detected this exact phrase in
    N out of M edits" beats "the model thought you meant ...".
LLM augmentation is a 1C-3 question, not a 1C-2 question.

Pipeline integration:
  - sender.send_approved_draft() and approver.reject() call
    mine_patterns(email_id=...) after compute_journey_metric.
  - Failure is non-fatal — wrapped at the call site.
  - Idempotent: re-running merges into existing 'open' rows; rows in
    'promoted' or 'dismissed' are never reopened by the miner.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Any

from app.db import execute, fetch_all, fetch_one

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# N-gram extraction
# ---------------------------------------------------------------------------

NGRAM_MIN = 3
NGRAM_MAX = 7

# Tokens that are noise on their own. We filter n-grams that are
# entirely stop-words (e.g. "of the and" → 100% stop). A 3-gram with one
# real word still survives.
_STOP = frozenset({
    "a", "an", "and", "as", "at", "be", "by", "for", "from",
    "has", "have", "i", "in", "is", "it", "of", "on", "or", "that",
    "the", "this", "to", "was", "were", "will", "with", "you", "your",
    "we", "our", "us", "are", "if", "but", "so", "do", "does", "not",
    "no", "yes", "any", "all", "can", "could", "would", "should",
    "may", "might", "shall",
})

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens. Drops punctuation, numbers, whitespace.

    Deterministic. Same input → same output. No model dependency.
    """
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


def _ngrams(tokens: list[str], n_min: int = NGRAM_MIN, n_max: int = NGRAM_MAX) -> set[str]:
    """All distinct n-grams of length n_min..n_max from the token list."""
    out: set[str] = set()
    if not tokens:
        return out
    L = len(tokens)
    for n in range(n_min, n_max + 1):
        if L < n:
            break
        for i in range(L - n + 1):
            gram = tokens[i : i + n]
            # Drop n-grams that are entirely stop-words — they're not signal.
            if all(t in _STOP for t in gram):
                continue
            out.add(" ".join(gram))
    return out


def _diff_ngrams(root_body: str, final_body: str) -> tuple[set[str], set[str]]:
    """Returns (removed, added) — n-grams in root but not final, and vice versa."""
    root = _ngrams(_tokenize(root_body))
    final = _ngrams(_tokenize(final_body))
    return root - final, final - root


# ---------------------------------------------------------------------------
# Journey traversal
# ---------------------------------------------------------------------------


def _journeys(email_id: int | None = None) -> list[dict[str, Any]]:
    """Pull terminal journeys from draft_metrics, joined to draft bodies.

    If email_id is given, only that journey is returned (per-journey hook).
    Otherwise all journeys, oldest first (full backfill / sanity gate).
    """
    if email_id is not None:
        sql = """
            SELECT m.email_id, m.service_line,
                   df.body AS first_body, dl.body AS final_body
              FROM draft_metrics m
              JOIN drafts df ON df.id = m.first_draft_id
              JOIN drafts dl ON dl.id = m.final_draft_id
             WHERE m.email_id = ?
             ORDER BY m.id ASC
        """
        return fetch_all(sql, (email_id,))
    sql = """
        SELECT m.email_id, m.service_line,
               df.body AS first_body, dl.body AS final_body
          FROM draft_metrics m
          JOIN drafts df ON df.id = m.first_draft_id
          JOIN drafts dl ON dl.id = m.final_draft_id
         ORDER BY m.id ASC
    """
    return fetch_all(sql)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _aggregate(journeys: list[dict[str, Any]]) -> dict[tuple[str | None, str, str], dict[str, Any]]:
    """Walk journeys and tally per (service_line, kind, text).

    Returns a dict keyed by the tuple, with values
      {'occurrences': int, 'sample_email_ids': [int]}
    """
    agg: dict[tuple[str | None, str, str], dict[str, Any]] = defaultdict(
        lambda: {"occurrences": 0, "sample_email_ids": []}
    )
    for j in journeys:
        sl = j.get("service_line")
        removed, added = _diff_ngrams(j.get("first_body") or "", j.get("final_body") or "")
        eid = int(j["email_id"])
        for text in removed:
            key = (sl, "removed_phrase", text)
            agg[key]["occurrences"] += 1
            if eid not in agg[key]["sample_email_ids"]:
                agg[key]["sample_email_ids"].append(eid)
        for text in added:
            key = (sl, "added_phrase", text)
            agg[key]["occurrences"] += 1
            if eid not in agg[key]["sample_email_ids"]:
                agg[key]["sample_email_ids"].append(eid)
    return agg


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

# Patterns surface only when they appear in this many distinct journeys.
# 1 = noise (one partner edit, no signal). 2 = the minimum that says
# "this happened twice independently". Easy to tune later.
MIN_OCCURRENCES = 2

# Cap on how many sample email_ids we store per pattern. The list is for
# the partner to click into examples — five is enough.
SAMPLE_CAP = 5


def _upsert_pattern(
    service_line: str | None,
    kind: str,
    text: str,
    occurrences: int,
    sample_email_ids: list[int],
) -> tuple[str, int]:
    """Insert or merge into patterns_log.

    Returns (action, id) where action is 'inserted' | 'merged' | 'skipped'.
    'skipped' fires when the existing row is 'promoted' or 'dismissed' —
    the partner has already judged this pattern, so the miner must not
    reopen it.
    """
    existing = fetch_one(
        """
        SELECT id, status, occurrences, sample_email_ids
          FROM patterns_log
         WHERE service_line IS ?
           AND pattern_kind = ?
           AND pattern_text = ?
        """,
        (service_line, kind, text),
    )
    if existing:
        if existing["status"] != "open":
            return ("skipped", int(existing["id"]))
        # Merge: keep the larger occurrence count (re-mining a journey shouldn't
        # double-count) and union the sample id lists, capped.
        try:
            old_samples = json.loads(existing["sample_email_ids"] or "[]")
            if not isinstance(old_samples, list):
                old_samples = []
        except json.JSONDecodeError:
            old_samples = []
        merged_samples = list(dict.fromkeys(old_samples + sample_email_ids))[:SAMPLE_CAP]
        merged_occurrences = max(int(existing["occurrences"]), occurrences)
        execute(
            """
            UPDATE patterns_log
               SET occurrences = ?,
                   sample_email_ids = ?
             WHERE id = ?
            """,
            (merged_occurrences, json.dumps(merged_samples), int(existing["id"])),
        )
        return ("merged", int(existing["id"]))

    cur = execute(
        """
        INSERT INTO patterns_log
          (service_line, pattern_kind, pattern_text, occurrences, sample_email_ids)
        VALUES (?,?,?,?,?)
        """,
        (service_line, kind, text, occurrences, json.dumps(sample_email_ids[:SAMPLE_CAP])),
    )
    return ("inserted", int(cur.lastrowid))


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def mine_patterns(email_id: int | None = None) -> dict[str, int]:
    """Run the miner. Returns a counters dict — useful for the sanity gate.

    Args:
      email_id: if given, only that journey is mined (pipeline hook).
                if None, every journey in draft_metrics is re-mined.

    Per-journey hook semantics: when called with email_id, a single
    journey can't satisfy MIN_OCCURRENCES on its own, so we additionally
    bump existing 'open' rows whose pattern matches this journey. This
    is what lets a pattern transition from "first time seen" to "seen
    twice → surface" naturally as new journeys arrive.
    """
    try:
        if email_id is None:
            journeys = _journeys()
            agg = _aggregate(journeys)
            counters = {"inserted": 0, "merged": 0, "skipped": 0, "below_threshold": 0}
            for (sl, kind, text), data in agg.items():
                if data["occurrences"] < MIN_OCCURRENCES:
                    counters["below_threshold"] += 1
                    continue
                action, _ = _upsert_pattern(sl, kind, text, data["occurrences"], data["sample_email_ids"])
                counters[action] = counters.get(action, 0) + 1
            logger.info(
                "pattern_miner full re-mine: journeys=%d candidates=%d %s",
                len(journeys), len(agg), counters,
            )
            return counters

        # Per-journey path. We need ALL journeys to know whether this email's
        # observed n-grams cross the threshold across history. Re-aggregate
        # everything (cheap — it's substring math over a few hundred bodies
        # at most) and persist the results.
        all_journeys = _journeys()
        agg = _aggregate(all_journeys)
        # Restrict persistence to keys this specific journey contributed to —
        # no point updating patterns this email had no role in.
        this_journey = _journeys(email_id)
        if not this_journey:
            return {"inserted": 0, "merged": 0, "skipped": 0, "below_threshold": 0}
        sl = this_journey[0].get("service_line")
        removed, added = _diff_ngrams(
            this_journey[0].get("first_body") or "",
            this_journey[0].get("final_body") or "",
        )
        relevant_keys = (
            {(sl, "removed_phrase", t) for t in removed}
            | {(sl, "added_phrase", t) for t in added}
        )
        counters = {"inserted": 0, "merged": 0, "skipped": 0, "below_threshold": 0}
        for key in relevant_keys:
            data = agg.get(key)
            if not data or data["occurrences"] < MIN_OCCURRENCES:
                counters["below_threshold"] += 1
                continue
            action, _ = _upsert_pattern(
                key[0], key[1], key[2], data["occurrences"], data["sample_email_ids"]
            )
            counters[action] = counters.get(action, 0) + 1
        logger.info(
            "pattern_miner email_id=%s: candidates=%d %s",
            email_id, len(relevant_keys), counters,
        )
        return counters
    except Exception as e:  # noqa: BLE001 — never block the pipeline
        logger.exception("mine_patterns failed (email_id=%s): %s", email_id, e)
        return {"error": 1}


# ---------------------------------------------------------------------------
# Lifecycle helpers — operator decisions from the dashboard.
# ---------------------------------------------------------------------------


def dismiss(pattern_id: int, *, decided_by: str = "prakasha") -> bool:
    """Mark a pattern dismissed. Won't be re-surfaced by the miner."""
    row = fetch_one("SELECT id, status FROM patterns_log WHERE id = ?", (pattern_id,))
    if not row:
        raise ValueError(f"pattern {pattern_id} not found")
    if row["status"] != "open":
        return False
    execute(
        "UPDATE patterns_log SET status = 'dismissed' WHERE id = ?",
        (pattern_id,),
    )
    logger.info("pattern %s dismissed by %s", pattern_id, decided_by)
    return True


def promote(pattern_id: int, *, decided_by: str = "prakasha") -> int:
    """Promote a pattern into a meta_rules row. Returns the new meta_rule id.

    The generated rule_text is descriptive and human-readable so Prakash
    sir can later inspect it in the meta_rules table without a translator.
    target_purpose='voice_example' because these are drafting patterns —
    they shape what the Drafter retrieves from knowledge_library.
    """
    row = fetch_one(
        "SELECT id, status, service_line, pattern_kind, pattern_text, occurrences "
        "FROM patterns_log WHERE id = ?",
        (pattern_id,),
    )
    if not row:
        raise ValueError(f"pattern {pattern_id} not found")
    if row["status"] != "open":
        raise ValueError(f"pattern {pattern_id} status is '{row['status']}', cannot promote")

    sl = row["service_line"]
    kind = row["pattern_kind"]
    text = row["pattern_text"]
    n = int(row["occurrences"])
    sl_label = sl or "all replies"

    if kind == "removed_phrase":
        rule_text = (
            f"Avoid the phrase \"{text}\" in {sl_label} — Prakasha sir removed "
            f"it in {n} edits."
        )
    else:  # added_phrase
        rule_text = (
            f"Prefer the phrase \"{text}\" in {sl_label} — Prakasha sir added "
            f"it in {n} edits."
        )

    cur = execute(
        """
        INSERT INTO meta_rules
          (rule_text, trigger_pattern, target_purpose, target_service_line,
           priority, is_active, created_by)
        VALUES (?,?,?,?,?,?,?)
        """,
        (rule_text, text, "voice_example", sl, 0, 1, "pattern_miner"),
    )
    meta_rule_id = int(cur.lastrowid)

    execute(
        """
        UPDATE patterns_log
           SET status = 'promoted',
               promoted_to_meta_rule_id = ?
         WHERE id = ?
        """,
        (meta_rule_id, pattern_id),
    )
    logger.info(
        "pattern %s promoted to meta_rule %s by %s",
        pattern_id, meta_rule_id, decided_by,
    )
    return meta_rule_id


# ---------------------------------------------------------------------------
# Read helpers — used by the /train panel.
# ---------------------------------------------------------------------------


def list_open_patterns(limit: int = 50) -> list[dict[str, Any]]:
    """Open patterns ordered by occurrences DESC, then most-recent."""
    rows = fetch_all(
        """
        SELECT id, service_line, pattern_kind, pattern_text, occurrences,
               sample_email_ids, created_at, updated_at
          FROM patterns_log
         WHERE status = 'open'
         ORDER BY occurrences DESC, updated_at DESC
         LIMIT ?
        """,
        (limit,),
    )
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["sample_email_ids_list"] = json.loads(d.get("sample_email_ids") or "[]")
        except json.JSONDecodeError:
            d["sample_email_ids_list"] = []
        out.append(d)
    return out


def counts_by_status() -> dict[str, int]:
    """{'open': n, 'promoted': n, 'dismissed': n} — for the /train header chip."""
    rows = fetch_all(
        "SELECT status, COUNT(*) AS n FROM patterns_log GROUP BY status"
    )
    out = {"open": 0, "promoted": 0, "dismissed": 0}
    for r in rows:
        out[r["status"]] = int(r["n"])
    return out
