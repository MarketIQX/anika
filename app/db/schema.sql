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
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    -- Phase 1A — promoted from runtime ALTER TABLE. Declared AFTER created_at
    -- to match live DB column order (the ALTER appended this column at the
    -- end of the original 13-column table). PRAGMA parity, same discipline
    -- as Phase 1B Cluster 2.
    is_web_form        INTEGER NOT NULL DEFAULT 0,  -- 1 = the mail was a website-form
                                                    --     notification and the sender/body
                                                    --     columns were substituted by the
                                                    --     parser. Sender uses this to
                                                    --     avoid threading the outbound
                                                    --     reply into Prakash sir's own inbox.
    -- Phase 1C-3 outbound-harvester columns (promoted from runtime ALTER).
    -- Position at end matches live DB column order (PRAGMA table_info parity).
    -- outbound_reply_gmail_id is the idempotency key: once set, the harvester
    -- never re-scans this thread. NULL = "not yet found / not yet checked".
    outbound_reply_gmail_id     TEXT DEFAULT NULL,
    outbound_reply_harvested_at TEXT DEFAULT NULL
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
    -- Phase 1B Cluster 7f: CHECK list expanded to match Category Literal in
    -- app/agents/schemas.py. Earlier weekend session added recruitment_enquiry
    -- and vendor_pitch to the Literal but not to this CHECK, which silently
    -- prevented those values from ever being persisted (and would have
    -- crashed the orchestrator the first time the classifier returned one).
    -- Cluster 7f also adds a runtime migration in init_db() that rewrites
    -- existing DBs whose CHECK still reflects the old 6-category list.
    category     TEXT NOT NULL CHECK (category IN (
        'new_enquiry','existing_client','sensitive',
        'recruitment_enquiry','vendor_pitch',
        'automated','spam','other'
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
    -- Phase 1C-3 added 'rejected_partner_replied_outside': the partner went
    -- around Anika and replied directly via Gmail before Anika's draft was
    -- approved. Set by app/jobs/outbound_harvester.py after harvesting the
    -- partner's free-typed body as a voice_example. Semantically distinct
    -- from 'rejected' (active dismissal): this means Anika's draft was
    -- bypassed, not judged. Existing DBs are migrated by
    -- _migrate_drafts_sent_status_check_constraint() in connection.py.
    sent_status     TEXT NOT NULL DEFAULT 'pending_approval'
                    CHECK (sent_status IN (
                        'pending_approval','approved','sending','sent','rejected',
                        'rejected_partner_replied_outside','edited','expired'
                    )),
    model           TEXT NOT NULL,
    prompt_version  INTEGER,
    reasoning       TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    -- Phase 1B cognitive-state columns (Cluster 2 — promoted from runtime ALTER).
    -- Position at end matches live DB column order (PRAGMA table_info parity).
    -- cognitive_state ∈ {'cold_start','learning','learned'} or NULL on legacy rows.
    -- Set by drafter.assemble_prompt() based on library.voice_coverage().
    -- (Nullable to match live DB shape from runtime ALTER TABLE history.)
    cognitive_state      TEXT DEFAULT NULL,
    -- Number of voice_example rows that backed this draft (joined to service_line).
    -- 0 ⇒ cold_start, 1-2 ⇒ learning, 3+ ⇒ learned.
    voice_coverage_count INTEGER DEFAULT 0
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
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    -- Soft-delete flag (Phase 1B Cluster 2 — promoted from runtime ALTER).
    -- Position at end matches live DB column order (PRAGMA table_info parity).
    -- 0 = deactivated; semantic_search filters on this so legacy seed rows
    -- can be retired without losing their forensic content.
    -- (Nullable to match live DB shape from runtime ALTER TABLE.)
    is_active       INTEGER DEFAULT 1
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
    processed_at     TEXT,
    -- Phase 1B confirmation-flow columns (Cluster 2 — promoted from runtime ALTER).
    -- Position at end matches live DB column order (PRAGMA table_info parity).
    -- Anika proposes a purpose for each upload and waits for user confirmation
    -- before promoting the unit into knowledge_library. These columns capture
    -- the proposal + the human-articulated uncertainty for the UI.
    -- (Columns nullable to match live DB shape from runtime ALTER TABLE history.)
    anika_proposed_purpose    TEXT DEFAULT NULL,
    anika_proposed_confidence REAL DEFAULT NULL,
    anika_reasoning           TEXT DEFAULT NULL,
    anika_suggested_sl        TEXT DEFAULT NULL,
    anika_suggested_custom    TEXT DEFAULT NULL,
    -- Output of the humility_layer agent: a 1-paragraph "what I noticed,
    -- what confuses me, what I would ask" articulation rendered on the
    -- Awaiting-Confirmation card.
    humility_articulation     TEXT DEFAULT NULL,
    -- 1 = waiting on user to confirm the proposed purpose; 0 = confirmed
    -- (and a knowledge_library row should now exist).
    awaiting_confirmation     INTEGER DEFAULT 1
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
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    -- Phase 1B purpose-classification columns (Cluster 2 — promoted from runtime ALTER).
    -- Position at end matches live DB column order (PRAGMA table_info parity).
    -- The Phase 1B teaching pipeline classifies each library row by *purpose*:
    --   voice_example | classifier_example | document_type | question_template |
    --   workflow_rule | firm_fact | firm_policy | reference_material
    -- The Drafter only retrieves entries whose purpose matches what it needs.
    -- (Columns nullable to match live DB shape from runtime ALTER TABLE history.)
    purpose                   TEXT DEFAULT 'voice_example',
    -- Anika's auto-proposed purpose + reasoning, before user confirmation.
    -- Surfaced in the "Awaiting your confirmation" UI section.
    anika_proposed_purpose    TEXT DEFAULT NULL,
    anika_proposed_confidence REAL DEFAULT NULL,
    anika_reasoning           TEXT DEFAULT NULL,
    -- The user's confirmed (or corrected) purpose. NULL until confirmation lands.
    user_confirmed_purpose    TEXT DEFAULT NULL,
    -- For purposes the user typed manually rather than choosing from the list.
    custom_purpose_label      TEXT DEFAULT NULL,
    is_custom_purpose         INTEGER DEFAULT 0,
    -- Phase 1C-3 — pathway attribution (orthogonal to created_by, which is the actor).
    --   'edit_approval'  = saved by approver after partner edited+approved a draft
    --   'gmail_outbound' = saved by outbound_harvester from a partner Gmail-direct send
    --   'manual_upload'  = uploaded via /train (or imported from a file)
    -- NULL on rows that pre-date this column (defaults to 'edit_approval' interpretation
    -- in UI rendering, which was the only path before this commit).
    harvest_source            TEXT DEFAULT NULL
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

-- ---------------------------------------------------------------------------
-- meta_rules — Phase 1B "rules about how Anika rules". Generated by the
-- meta_rule_generator agent when a user-confirmed correction implies a rule
-- that should fire on future inputs (e.g. "every queue item whose body
-- mentions GST without service_line should default to gst_indirect").
--
-- Phase 1B Cluster 2 — promoted from runtime CREATE TABLE in scratch scripts.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS meta_rules (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text           TEXT NOT NULL,           -- human-readable statement of the rule
    trigger_pattern     TEXT,                    -- substring/regex that activates the rule
    target_purpose      TEXT NOT NULL,           -- which library purpose this rule applies to
    target_service_line TEXT,                    -- optional service-line filter
    priority            INTEGER DEFAULT 0,
    is_active           INTEGER DEFAULT 1,
    applied_count      INTEGER DEFAULT 0,
    created_by          TEXT NOT NULL,           -- user email (or 'meta_rule_generator')
    deleted_by          TEXT,
    deleted_at          TEXT,
    created_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at          TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_meta_active ON meta_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_meta_purpose ON meta_rules(target_purpose);

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

-- ---------------------------------------------------------------------------
-- Phase 1C-1: self-measurement.
--
-- draft_metrics — one row per email-journey that reaches a terminal state
-- (sent or rejected). Captures the edit-distance between Anika's first
-- draft for that email and the FINAL state of the draft chain — i.e. how
-- much human-correction was needed before approval.
--
-- Lower edit_distance over time per service_line ⇒ Anika is genuinely
-- learning that service's voice. This table is the data substrate for the
-- /train/learning-curves panel and (in Phase 1C-2) for the pattern-
-- recognition agent.
--
-- Why "journey" not "per draft": one approval can sit at the end of a
-- chain (first draft → edit → second draft → approve). The journey metric
-- captures the WHOLE conversation Anika had with the partner — that's
-- what reflects learning, not any single round.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS draft_metrics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id              INTEGER NOT NULL REFERENCES raw_emails(id) ON DELETE CASCADE,
    -- Root of the draft chain (parent_draft_id IS NULL) — Anika's first attempt.
    first_draft_id        INTEGER NOT NULL REFERENCES drafts(id),
    -- Tip of the chain — the draft that was approved (sent) or rejected.
    final_draft_id        INTEGER NOT NULL REFERENCES drafts(id),
    -- Terminal state of the journey.
    final_outcome         TEXT NOT NULL CHECK (final_outcome IN ('sent','rejected')),
    -- Snapshots from the FIRST draft (so we can compare same-state drafts).
    service_line          TEXT,
    cognitive_state       TEXT,                 -- cold_start | learning | learned | NULL
    voice_coverage_count  INTEGER,
    -- Length of the draft chain. 1 = approved/rejected on first attempt.
    chain_length          INTEGER NOT NULL DEFAULT 1,
    -- SequenceMatcher-based: 1.0 - similarity_ratio between first.body and
    -- final.body. 0.0 = identical (no edit needed). 1.0 = complete rewrite.
    -- For 'rejected' journeys we still compute it from first.body to
    -- final.body — even a rejection captures "how far apart was Anika's
    -- attempt from what got dismissed".
    edit_distance         REAL,
    similarity_ratio      REAL,
    -- Wall-clock duration from first draft to terminal state, in seconds.
    duration_seconds      INTEGER,
    created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_draft_metrics_service ON draft_metrics(service_line);
CREATE INDEX IF NOT EXISTS idx_draft_metrics_outcome ON draft_metrics(final_outcome);
CREATE INDEX IF NOT EXISTS idx_draft_metrics_created ON draft_metrics(created_at);

-- ---------------------------------------------------------------------------
-- reflection_log — Phase 1C-1 schema placeholder for Phase 1C-2.
--
-- Captures Anika's own narrative observations about her performance over
-- time, e.g. "Edit distance for nri_tax over the last 5 sent drafts:
-- 0.32 → 0.28 → 0.21 → 0.18 → 0.15. Trending down — voice is being
-- learned." 1C-1 only sets up the table; the writer (a self-reflection
-- agent that scans draft_metrics for trends) lands in 1C-2.
--
-- Distinct from reasoning_log (which captures per-call decisions) —
-- reflection_log captures aggregate observations Anika makes ABOUT
-- herself. The Drafter reads recent reflections in 1C-2 to inform
-- prompt assembly, closing the meta-cognitive loop.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reflection_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Service line the reflection concerns (NULL = universal observation).
    service_line     TEXT,
    -- Type of observation: edit_distance_trend, voice_coverage_milestone,
    -- cognitive_state_transition, edit_pattern, etc.
    observation_type TEXT NOT NULL,
    -- Human-readable narrative — meant to be read on the Train tab.
    narrative        TEXT NOT NULL,
    -- Raw numbers that backed the narrative (JSON).
    numeric_data     TEXT NOT NULL DEFAULT '{}',
    -- Whether this reflection has been incorporated into the active
    -- Drafter prompt (used in 1C-2 to avoid double-injecting).
    incorporated     INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_reflection_service ON reflection_log(service_line);
CREATE INDEX IF NOT EXISTS idx_reflection_type ON reflection_log(observation_type);
CREATE INDEX IF NOT EXISTS idx_reflection_created ON reflection_log(created_at);

-- ---------------------------------------------------------------------------
-- patterns_log — Phase 1C-2 pattern recognition.
--
-- Substring-based observations the pattern_miner extracts from terminal
-- draft journeys: when the partner consistently REMOVES or ADDS the same
-- 3-7 word phrase across multiple edits in the same service line, that's
-- a real pattern worth surfacing. The Train tab lists open patterns; the
-- partner can either dismiss them or promote them into a meta_rule.
--
-- Status lifecycle (deliberately small — three states is enough):
--   open       — surfaced by miner, awaiting partner judgement
--   promoted   — partner turned it into a meta_rule (id stored)
--   dismissed  — partner said "not a real signal" — never re-surface
--
-- pattern_kind:
--   removed_phrase — n-gram present in root draft, absent from final
--   added_phrase   — n-gram absent from root, present in final
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS patterns_log (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    service_line             TEXT,                                 -- NULL = universal
    pattern_kind             TEXT NOT NULL CHECK (pattern_kind IN ('removed_phrase','added_phrase')),
    pattern_text             TEXT NOT NULL,                        -- the actual n-gram
    occurrences              INTEGER NOT NULL DEFAULT 1,           -- # of journeys exhibiting this
    sample_email_ids         TEXT NOT NULL DEFAULT '[]',           -- JSON array, capped at 5
    status                   TEXT NOT NULL DEFAULT 'open'
                             CHECK (status IN ('open','promoted','dismissed')),
    promoted_to_meta_rule_id INTEGER REFERENCES meta_rules(id),    -- set when promoted
    created_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    -- Same (service_line, pattern_kind, pattern_text) tuple is a single observation
    -- whose occurrences accumulate over time. Re-mining merges into existing rows.
    UNIQUE (service_line, pattern_kind, pattern_text)
);
CREATE INDEX IF NOT EXISTS idx_patterns_status ON patterns_log(status);
CREATE INDEX IF NOT EXISTS idx_patterns_service ON patterns_log(service_line);
CREATE INDEX IF NOT EXISTS idx_patterns_created ON patterns_log(created_at);

-- Keep patterns_log.updated_at fresh whenever occurrences/status/sample changes.
DROP TRIGGER IF EXISTS patterns_touch_updated_at;
CREATE TRIGGER patterns_touch_updated_at
AFTER UPDATE ON patterns_log
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE patterns_log SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = NEW.id;
END;

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
