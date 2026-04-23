-- Anika — SQLite schema.
--
-- Design principles:
--   1. Every table has created_at so we can reconstruct the timeline.
--   2. Agent outputs are stored as structured columns AND the raw JSON
--      reasoning, so the dashboard can show both "what" and "why".
--   3. Approval gate is enforced by a trigger on `drafts` (see bottom).
--   4. reasoning_log and sent_log are append-only — no UPDATE/DELETE in app code.
--
-- All timestamps are ISO-8601 strings in UTC. The UI converts to Asia/Kolkata.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ---------------------------------------------------------------------------
-- Inbox ingestion
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS raw_emails (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_message_id   TEXT NOT NULL UNIQUE,
    gmail_thread_id    TEXT NOT NULL,
    from_email         TEXT NOT NULL,   -- post-substitution: real enquirer if web form
    from_name          TEXT,            -- post-substitution
    to_email           TEXT NOT NULL,
    cc                 TEXT,
    subject            TEXT,
    body_plain         TEXT,            -- post-substitution: parsed message if web form
    body_html          TEXT,
    snippet            TEXT,
    received_at        TEXT NOT NULL,
    is_reply_in_thread INTEGER NOT NULL DEFAULT 0,
    is_web_form        INTEGER NOT NULL DEFAULT 0,  -- 1 = the mail was a website-form
                                                    --     notification and the sender/body
                                                    --     columns were substituted by the
                                                    --     parser. Sender uses this to
                                                    --     avoid threading the outbound
                                                    --     reply into Prakash sir's own inbox.
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_raw_emails_received ON raw_emails(received_at);
CREATE INDEX IF NOT EXISTS idx_raw_emails_from ON raw_emails(from_email);

-- ---------------------------------------------------------------------------
-- Classifier — which of 5 buckets does this email fall into?
--   new_enquiry | existing_client | sensitive | automated | spam
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS classifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id     INTEGER NOT NULL REFERENCES raw_emails(id) ON DELETE CASCADE,
    category     TEXT NOT NULL CHECK (category IN (
        'new_enquiry','existing_client','sensitive','automated','spam','other'
    )),
    confidence   REAL NOT NULL,
    reasoning    TEXT,
    model        TEXT NOT NULL,
    prompt_version INTEGER,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_classifications_email ON classifications(email_id);

-- ---------------------------------------------------------------------------
-- Enricher — structured sender intelligence
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS enrichments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id          INTEGER NOT NULL REFERENCES raw_emails(id) ON DELETE CASCADE,
    sender_name       TEXT,
    sender_org        TEXT,
    sender_country    TEXT,
    likely_service_line TEXT,   -- nri_tax | foreign_subsidiary | transfer_pricing | virtual_cfo | other
    urgency           TEXT CHECK (urgency IN ('hot','warm','cold') OR urgency IS NULL),
    routing_partner   TEXT,     -- from firm_profile routing matrix
    similar_memories  TEXT,     -- JSON array of memory.id values used as few-shot
    client_match_id   INTEGER,  -- non-null if sender matches an existing clients row
    summary           TEXT,     -- 2-line synopsis for the approval card
    reasoning         TEXT,
    model             TEXT NOT NULL,
    prompt_version    INTEGER,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_enrichments_email ON enrichments(email_id);

-- ---------------------------------------------------------------------------
-- Drafts — the reply text Anika wants to send
--
-- sent_status lifecycle:
--   pending_approval -> approved -> sending -> sent
--                     \-> rejected
--                     \-> edited (new draft row is created, this row stays at 'edited')
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS drafts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id        INTEGER NOT NULL REFERENCES raw_emails(id) ON DELETE CASCADE,
    parent_draft_id INTEGER REFERENCES drafts(id),  -- set if this draft is a re-draft after edit
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    tone_notes      TEXT,
    uses_signature  INTEGER NOT NULL DEFAULT 1,
    sent_status     TEXT NOT NULL DEFAULT 'pending_approval'
                    CHECK (sent_status IN (
                        'pending_approval','approved','sending','sent','rejected','edited','expired'
                    )),
    model           TEXT NOT NULL,
    prompt_version  INTEGER,
    reasoning       TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_drafts_email ON drafts(email_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(sent_status);

-- Approval gate — each draft may have exactly one decision row per outcome.
--
-- decision:
--   approved  — Prakash sir tapped Send (or approved an edited draft)
--   edited    — Prakash sir gave an edit instruction; a new draft was generated
--   rejected  — Prakash sir dismissed the draft; enquiry needs manual handling

CREATE TABLE IF NOT EXISTS approvals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id         INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    decision         TEXT NOT NULL CHECK (decision IN ('approved','edited','rejected')),
    decided_by       TEXT NOT NULL,            -- 'prakasha' by default
    edit_instruction TEXT,                     -- only for decision='edited'
    edit_category    TEXT,                     -- style | fact | context | rejection (set by learner)
    edit_delta_json  TEXT,                     -- JSON diff {before, after, changes[]} computed by learner
    user_agent       TEXT,
    ip_address       TEXT,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_approvals_draft ON approvals(draft_id);
CREATE INDEX IF NOT EXISTS idx_approvals_decision ON approvals(decision);

-- Audit trail of actual sends.
-- Append-only: enforced by a trigger below (no updates, no deletes).
CREATE TABLE IF NOT EXISTS sent_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id        INTEGER NOT NULL REFERENCES drafts(id),
    email_id        INTEGER NOT NULL REFERENCES raw_emails(id),
    approval_id     INTEGER NOT NULL REFERENCES approvals(id),
    gmail_message_id TEXT,                     -- returned by Gmail API after send
    gmail_thread_id  TEXT,
    to_email        TEXT NOT NULL,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    sent_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    test_mode       INTEGER NOT NULL DEFAULT 0 -- 1 if ANIKA_TEST_MODE was on (no real API call)
);
CREATE INDEX IF NOT EXISTS idx_sent_log_draft ON sent_log(draft_id);
CREATE INDEX IF NOT EXISTS idx_sent_log_sent_at ON sent_log(sent_at);

-- ---------------------------------------------------------------------------
-- Memory Core — canonical approved drafts + curated examples, with embeddings
--
-- memory holds the content. memory_vec holds the embedding vector (sqlite-vec).
-- We use sqlite-vec instead of sqlite-vss because sqlite-vss has no Windows wheels;
-- the embedding semantics are identical (cosine / L2 over float32 vectors).
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kind            TEXT NOT NULL CHECK (kind IN (
        'approved_draft','exemplar','rule_note','firm_snippet'
    )),
    service_line    TEXT,                      -- nri_tax | foreign_subsidiary | transfer_pricing | virtual_cfo | other
    subject         TEXT,
    content         TEXT NOT NULL,             -- the actual text that gets retrieved for few-shot
    source_email_id INTEGER REFERENCES raw_emails(id),
    source_draft_id INTEGER REFERENCES drafts(id),
    tags            TEXT,                      -- JSON array of lowercase tags
    embedding_model TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_memory_service ON memory(service_line);
CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory(kind);

-- Virtual vec table created at runtime by db.connect() because the
-- extension must be loaded first. Schema documented here for reference:
--   CREATE VIRTUAL TABLE memory_vec USING vec0(
--       memory_id INTEGER PRIMARY KEY,
--       embedding FLOAT[1536]
--   );

-- ---------------------------------------------------------------------------
-- Self-evolving prompts — every agent reads the latest active row
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_prompts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name   TEXT NOT NULL,    -- classifier | enricher | drafter | learner | approver
    version      INTEGER NOT NULL,
    prompt_text  TEXT NOT NULL,
    change_note  TEXT,             -- human-readable reason for this version
    is_active    INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (agent_name, version)
);
CREATE INDEX IF NOT EXISTS idx_prompts_agent_active ON agent_prompts(agent_name, is_active);

-- ---------------------------------------------------------------------------
-- Reasoning log — every agent call produces one row.
-- Append-only: no UPDATE/DELETE from app code (enforced by trigger).
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reasoning_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name     TEXT NOT NULL,
    email_id       INTEGER REFERENCES raw_emails(id),
    draft_id       INTEGER REFERENCES drafts(id),
    input_json     TEXT NOT NULL,
    output_json    TEXT,
    reasoning_text TEXT,
    model          TEXT,
    prompt_version INTEGER,
    latency_ms     INTEGER,
    status         TEXT NOT NULL CHECK (status IN ('ok','error')) DEFAULT 'ok',
    error_text     TEXT,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_reasoning_email ON reasoning_log(email_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_agent ON reasoning_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_reasoning_created ON reasoning_log(created_at);

-- ---------------------------------------------------------------------------
-- Clients — existing Balakrishna clients for VIP / existing-client detection
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS clients (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT NOT NULL UNIQUE,
    name           TEXT,
    organisation   TEXT,
    country        TEXT,
    is_vip         INTEGER NOT NULL DEFAULT 0,   -- 1 = summary-only, no auto-draft
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ---------------------------------------------------------------------------
-- Firm knowledge base — key/value facts about Balakrishna & Co.
-- Anika reads this as ground truth. Loaded from docs/03_firm_profile.md on boot.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS firm_knowledge (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    key          TEXT NOT NULL UNIQUE,
    value        TEXT NOT NULL,
    category     TEXT,         -- identity | team | service | tone | faq | signature | ...
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ---------------------------------------------------------------------------
-- Rules — do's, don'ts, sensitive keywords, FAQs, thresholds.
--
-- rule_type:
--   blacklist_topic   — if email body matches `pattern`, bypass Anika
--   rupee_threshold   — if email body mentions amount above `threshold_value`, bypass
--   tone_do           — positive writing rule
--   tone_dont         — negative writing rule
--   faq               — verbatim answer
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type       TEXT NOT NULL,
    pattern         TEXT,           -- regex or substring
    threshold_value REAL,
    text_value      TEXT,           -- FAQ answer or tone rule body
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_rules_type_active ON rules(rule_type, is_active);

-- ---------------------------------------------------------------------------
-- System state — kill switch, counters, last-poll cursor.
-- Single-row-per-key KV store.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS system_state (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL,
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ---------------------------------------------------------------------------
-- TEACHING SYSTEM (v2) — Prakasha sir teaches Anika like onboarding a junior.
--
-- Flow:
--   1. User pastes text or uploads files  -> teaching_queue row (status=pending)
--   2. Learner extracts units + clarifications -> units saved as knowledge_library
--      rows (status=approved) OR queued as clarifications rows (status=pending)
--   3. User answers clarifications -> knowledge_library rows promoted to active
--   4. Drafter retrieves from knowledge_library at draft time via embeddings
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS teaching_queue (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_content      TEXT NOT NULL,       -- plain-text extract of text+files
    source_type      TEXT NOT NULL CHECK (source_type IN ('text','file')),
    file_mime        TEXT,                -- for file uploads
    original_filename TEXT,               -- original upload filename (safe-echo back)
    stored_path      TEXT,                -- relative path under data/uploads/
    status           TEXT NOT NULL CHECK (status IN (
        'pending','processing','needs_clarification','approved','rejected','failed'
    )) DEFAULT 'pending',
    error_text       TEXT,                -- populated on 'failed'
    created_by_user  TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    processed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_tq_status ON teaching_queue(status);
CREATE INDEX IF NOT EXISTS idx_tq_created ON teaching_queue(created_at);

CREATE TABLE IF NOT EXISTS knowledge_library (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    kind             TEXT NOT NULL CHECK (kind IN ('rule','example','fact','policy')),
    content          TEXT NOT NULL,
    service_line     TEXT,                -- freetext, e.g. 'nri_tax','foreign_subsidiary'
    scope            TEXT NOT NULL CHECK (scope IN ('universal','service_line'))
                                            DEFAULT 'universal',
    source_queue_id  INTEGER REFERENCES teaching_queue(id),
    confidence       REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0.0 AND 1.0),
    applied_count    INTEGER NOT NULL DEFAULT 0,
    last_used_at     TEXT,
    is_active        INTEGER NOT NULL DEFAULT 1,   -- 0 = soft-deleted
    created_by       TEXT,                         -- user email that created the entry
    deleted_by       TEXT,                         -- user email that soft-deleted
    deleted_at       TEXT,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_kl_active ON knowledge_library(is_active);
CREATE INDEX IF NOT EXISTS idx_kl_kind ON knowledge_library(kind);
CREATE INDEX IF NOT EXISTS idx_kl_scope ON knowledge_library(scope);
CREATE INDEX IF NOT EXISTS idx_kl_service_line ON knowledge_library(service_line);

CREATE TABLE IF NOT EXISTS clarifications (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id           INTEGER NOT NULL REFERENCES teaching_queue(id) ON DELETE CASCADE,
    question_text      TEXT NOT NULL,
    options_json       TEXT NOT NULL DEFAULT '[]',   -- [] means freetext
    target_unit_index  INTEGER NOT NULL,             -- which unit in the queue row this belongs to
    unit_preview       TEXT,                         -- snippet of the ambiguous unit content
    answer             TEXT,
    status             TEXT NOT NULL CHECK (status IN ('pending','answered','skipped'))
                                            DEFAULT 'pending',
    asked_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    answered_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_clar_status ON clarifications(status);
CREATE INDEX IF NOT EXISTS idx_clar_queue ON clarifications(queue_id);

-- Keep knowledge_library.updated_at fresh (parallels drafts_touch_updated_at)
DROP TRIGGER IF EXISTS kl_touch_updated_at;
CREATE TRIGGER kl_touch_updated_at
AFTER UPDATE ON knowledge_library
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE knowledge_library SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = NEW.id;
END;

-- ---------------------------------------------------------------------------
-- Dashboard users — bcrypt-hashed passwords, simple role model.
--
-- role:
--   admin  — AK (MarketIQX). Full dashboard access.
--   user   — Prakash sir. Drafts / Inbox / limited Settings only.
--
-- Passwords are never stored in plaintext. password_hash holds a bcrypt hash.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK (role IN ('admin','user')),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_login_at  TEXT
);

-- ---------------------------------------------------------------------------
-- Access log — append-only audit trail for logins, logouts, approvals,
-- kill-switch toggles, and settings writes.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS access_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email   TEXT,               -- NULL for anonymous (failed login) events
    action       TEXT NOT NULL,      -- e.g. 'login_success','login_failure','logout',
                                     --      'draft_approve','draft_reject','draft_edit',
                                     --      'kill_switch_on','kill_switch_off',
                                     --      'vip_add','vip_remove','client_delete',
                                     --      'gmail_oauth_start','gmail_oauth_complete',
                                     --      'memory_backfill','poll_now'
    target       TEXT,               -- e.g. draft_id or client email (free-form)
    ip_address   TEXT,
    user_agent   TEXT,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_access_log_user ON access_log(user_email);
CREATE INDEX IF NOT EXISTS idx_access_log_action ON access_log(action);
CREATE INDEX IF NOT EXISTS idx_access_log_created ON access_log(created_at);

-- Append-only — block UPDATE and DELETE on access_log.
DROP TRIGGER IF EXISTS access_log_no_update;
CREATE TRIGGER access_log_no_update
BEFORE UPDATE ON access_log
BEGIN
    SELECT RAISE(ABORT, 'access_log is append-only');
END;

DROP TRIGGER IF EXISTS access_log_no_delete;
CREATE TRIGGER access_log_no_delete
BEFORE DELETE ON access_log
BEGIN
    SELECT RAISE(ABORT, 'access_log is append-only');
END;

-- ---------------------------------------------------------------------------
-- CRITICAL: the approval gate.
--
-- This trigger is the hard guarantee that no email can be marked 'sent'
-- without a matching approvals row (decision='approved'). It is enforced
-- at the database layer so application bugs cannot bypass it.
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS enforce_approval_before_send;
CREATE TRIGGER enforce_approval_before_send
BEFORE UPDATE ON drafts
FOR EACH ROW
WHEN NEW.sent_status = 'sent' AND OLD.sent_status != 'sent'
BEGIN
    SELECT RAISE(ABORT, 'Cannot mark as sent without approval row')
    WHERE NOT EXISTS (
        SELECT 1 FROM approvals
        WHERE draft_id = NEW.id
          AND decision = 'approved'
    );
END;

-- Append-only trigger on sent_log — block UPDATE and DELETE
DROP TRIGGER IF EXISTS sent_log_no_update;
CREATE TRIGGER sent_log_no_update
BEFORE UPDATE ON sent_log
BEGIN
    SELECT RAISE(ABORT, 'sent_log is append-only');
END;

DROP TRIGGER IF EXISTS sent_log_no_delete;
CREATE TRIGGER sent_log_no_delete
BEFORE DELETE ON sent_log
BEGIN
    SELECT RAISE(ABORT, 'sent_log is append-only');
END;

-- Append-only trigger on reasoning_log — block UPDATE and DELETE
DROP TRIGGER IF EXISTS reasoning_log_no_update;
CREATE TRIGGER reasoning_log_no_update
BEFORE UPDATE ON reasoning_log
BEGIN
    SELECT RAISE(ABORT, 'reasoning_log is append-only');
END;

DROP TRIGGER IF EXISTS reasoning_log_no_delete;
CREATE TRIGGER reasoning_log_no_delete
BEFORE DELETE ON reasoning_log
BEGIN
    SELECT RAISE(ABORT, 'reasoning_log is append-only');
END;

-- Keep drafts.updated_at fresh
DROP TRIGGER IF EXISTS drafts_touch_updated_at;
CREATE TRIGGER drafts_touch_updated_at
AFTER UPDATE ON drafts
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE drafts SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = NEW.id;
END;
