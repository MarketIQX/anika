# Phase 1B Stabilization Audit

Generated: 2026-04-26 09:09:34 UTC

## 1. Git State

- Current branch: `master`
- Current commit: `eddbc66` (eddbc66e6c8c2ecf52104158991a94696dcc8a27)
- Last tag: `phase-1a-complete`
- All tags: `phase-1a-complete
pre-learner-refactor`
- Uncommitted changes: 204

```
M app/agents/approver.py
 M app/agents/classifier.py
 M app/agents/drafter.py
 M app/agents/enricher.py
 M app/agents/orchestrator.py
 M app/agents/schemas.py
 M app/agents/teaching_learner.py
 M app/auth/middleware.py
 M app/cognitive/library.py
 M app/cognitive/teaching.py
 M app/dashboard/routes.py
 M app/dashboard/templates/base.html
 M app/dashboard/templates/draft_detail.html
 M app/dashboard/templates/train.html
 M app/jobs/backfill_memory.py
 M app/main.py
 M app/tools/gmail_tool.py
 M app/tools/knowledge_tool.py
 M app/tools/notify_tool.py
 M check.py
 M cleanup.py
?? adaptation_audit.py
?? add_dashboard_route.py
?? add_finalize_with_purpose.py
?? add_graph_route.py
?? add_page_visit.py
?? add_progress_tab.py
?? add_progress_tab_v2.py
?? add_rules_nav.py
?? add_rules_routes.py
... (174 more)
```

## 2. Files Modified Since `phase-1a-complete`

(no committed changes since tag)

### Files with uncommitted changes:
- `M app/agents/approver.py`
- ` M app/agents/classifier.py`
- ` M app/agents/drafter.py`
- ` M app/agents/enricher.py`
- ` M app/agents/orchestrator.py`
- ` M app/agents/schemas.py`
- ` M app/agents/teaching_learner.py`
- ` M app/auth/middleware.py`
- ` M app/cognitive/library.py`
- ` M app/cognitive/teaching.py`
- ` M app/dashboard/routes.py`
- ` M app/dashboard/templates/base.html`
- ` M app/dashboard/templates/draft_detail.html`
- ` M app/dashboard/templates/train.html`
- ` M app/jobs/backfill_memory.py`
- ` M app/main.py`
- ` M app/tools/gmail_tool.py`
- ` M app/tools/knowledge_tool.py`
- ` M app/tools/notify_tool.py`
- ` M check.py`
- ` M cleanup.py`
- `?? adaptation_audit.py`
- `?? add_dashboard_route.py`
- `?? add_finalize_with_purpose.py`
- `?? add_graph_route.py`
- `?? add_page_visit.py`
- `?? add_progress_tab.py`
- `?? add_progress_tab_v2.py`
- `?? add_rules_nav.py`
- `?? add_rules_routes.py`
- `?? add_visit_logger.py`
- `?? app/agents/duplicate_judge.py`
- `?? app/agents/humility_layer.py`
- `?? app/agents/meta_rule_generator.py`
- `?? app/agents/purpose_classifier.py`
- `?? app/dashboard/templates/knowledge_graph.html`
- `?? app/dashboard/templates/review_rule.html`
- `?? app/dashboard/templates/rule_form.html`
- `?? app/dashboard/templates/rules.html`
- `?? app/dashboard/templates/teaching_dashboard.html`
- `?? app/guardrails/structural_validator.py`
- `?? audit_gmail_writes.py`
- `?? audit_legacy_rules.py`
- `?? audit_prakasha.py`
- `?? audit_signature_drift.py`
- `?? audit_uncertainty.py`
- `?? backfill_state.py`
- `?? build_validator.py`
- `?? check_876.py`
- `?? check_activity.py`
- `?? check_both.py`
- `?? check_draft25_sigs.py`
- `?? check_drafts.py`
- `?? check_his_edits.py`
- `?? check_prakasha_activity.py`
- `?? check_prasad.py`
- `?? check_preview.py`
- `?? check_queue.py`
- `?? check_retrieve_rules.py`
- `?? clean_orphan.py`
- `?? cleanup_db.py`
- `?? cleanup_inbox.py`
- `?? cleanup_noise.py`
- `?? close_stale_clarifications.py`
- `?? create_prasad.py`
- `?? deep_diagnose_sumana.py`
- `?? diag.py`
- `?? diag_banner.py`
- `?? diag_double_sig.py`
- `?? diag_enricher.py`
- `?? diag_finalize.py`
- `?? diag_learner.py`
- `?? diag_skip.py`
- `?? engagement_report.py`
- `?? find_answer_clar.py`
- `?? find_callers.py`
- `?? find_inbox.py`
- `?? find_insert.py`
- `?? find_notification.py`
- `?? find_prompt.py`
- `?? fix_active_tab.py`
- `?? fix_attribution.py`
- `?? fix_banner.py`
- `?? fix_draft25.py`
- `?? fix_endif.py`
- `?? fix_enricher.py`
- `?? fix_humility_v2.py`
- `?? fix_last_retrieve.py`
- `?? fix_notify_restore.py`
- `?? fix_queue_12.py`
- `?? fix_signature_root.py`
- `?? fix_skip_path.py`
- `?? fix_status_constraint.py`
- `?? full_diag.py`
- `?? inspect_classifier.py`
- `?? inspect_dispatch.py`
- `?? inspect_middleware.py`
- `?? inspect_msg_type.py`
- `?? investigate_leak.py`
- `?? investigate_learner.py`
- `?? investigate_quality.py`
- `?? learning_check.py`
- `?? live_tracker.py`
- `?? make_dashboard_template.py`
- `?? make_graph_template.py`
- `?? make_rule_form_template.py`
- `?? make_rules_template.py`
- `?? monitor_prakasha.py`
- `?? morning_check.py`
- `?? partner_activity.py`
- `?? patch_answer.py`
- `?? patch_clarification_ui.py`
- `?? patch_dedup.py`
- `?? patch_fallback.py`
- `?? patch_filter.py`
- `?? patch_gmail_v2.py`
- `?? patch_inbox_strict.py`
- `?? patch_inbox_view.py`
- `?? patch_learner.py`
- `?? patch_notify.py`
- `?? patch_notify_v2.py`
- `?? patch_notify_v3.py`
- `?? patch_orch_gate.py`
- `?? patch_orch_step1.py`
- `?? patch_recruitment_filter.py`
- `?? patch_save_stripping.py`
- `?? patch_unknown.py`
- `?? patch_voice_save.py`
- `?? prakasha_activity.py`
- `?? prasad_journey.py`
- `?? prasad_now.py`
- `?? promote.py`
- `?? promote2.py`
- `?? qc_mangalam.py`
- `?? qc_report.py`
- `?? quick_check.py`
- `?? real_adaptation_check.py`
- `?? reject_27.py`
- `?? reset_ak.py`
- `?? restore.py`
- `?? retest_humility.py`
- `?? retry_atulya_safe.py`
- `?? retry_atulya_v2.py`
- `?? retry_atulya_v3.py`
- `?? root_cause.py`
- `?? see_damage.py`
- `?? see_dispatch.py`
- `?? see_notify_now.py`
- `?? see_sumana.py`
- `?? show_draft_detail.py`
- `?? show_file_flow.py`
- `?? show_finalize.py`
- `?? show_learning_engine.py`
- `?? show_memory_tool.py`
- `?? show_meta_rules_schema.py`
- `?? show_notify.py`
- `?? show_retrieve.py`
- `?? show_semantic_search.py`
- `?? show_teach_route.py`
- `?? sim.py`
- `?? stabilization_audit.py`
- `?? state_check.py`
- `?? step1_schema.py`
- `?? step2_helper.py`
- `?? step3a_drafter_prompt.py`
- `?? step3b_caller.py`
- `?? step3b_fix.py`
- `?? step4_insert.py`
- `?? step5_banner.py`
- `?? step6_deactivate_legacy.py`
- `?? strip_lib_sig.py`
- `?? strip_old_sigs.py`
- `?? task1_add_purpose.py`
- `?? task2_classification_columns.py`
- `?? task3_custom_label.py`
- `?? task4_meta_rules.py`
- `?? task5_migrate.py`
- `?? task6_classifier.py`
- `?? task7a_meta_gen.py`
- `?? task7b_step1.py`
- `?? task7b_step2.py`
- `?? task7b_step3.py`
- `?? task7b_step4.py`
- `?? task7b_step5.py`
- `?? task9_drafter_filter.py`
- `?? test_classifier.py`
- `?? test_dedup.py`
- `?? test_humility.py`
- `?? test_meta_rules.py`
- `?? test_voice_save.py`
- `?? time_check.py`
- `?? trace_callers.py`
- `?? trace_signature.py`
- `?? triage.py`
- `?? update_confirm_route.py`
- `?? verify_clean_sig.py`
- `?? verify_confirm.py`
- `?? verify_draft26.py`
- `?? verify_drafter_filter.py`
- `?? verify_restore.py`
- `?? verify_skip.py`
- `?? visits.py`
- `?? watch.py`
- `?? who_loggedin.py`

## 3. Database Schema

All tables and their columns (current state):

### `access_log`
```
  id                             INTEGER         PRIMARY KEY
  user_email                     TEXT           
  action                         TEXT            NOT NULL
  target                         TEXT           
  ip_address                     TEXT           
  user_agent                     TEXT           
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 197

### `agent_prompts`
```
  id                             INTEGER         PRIMARY KEY
  agent_name                     TEXT            NOT NULL
  version                        INTEGER         NOT NULL
  prompt_text                    TEXT            NOT NULL
  change_note                    TEXT           
  is_active                      INTEGER         NOT NULL DEFAULT 0
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 8

### `approvals`
```
  id                             INTEGER         PRIMARY KEY
  draft_id                       INTEGER         NOT NULL
  decision                       TEXT            NOT NULL
  decided_by                     TEXT            NOT NULL
  edit_instruction               TEXT           
  edit_category                  TEXT           
  edit_delta_json                TEXT           
  user_agent                     TEXT           
  ip_address                     TEXT           
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 20

### `clarifications`
```
  id                             INTEGER         PRIMARY KEY
  queue_id                       INTEGER         NOT NULL
  question_text                  TEXT            NOT NULL
  options_json                   TEXT            NOT NULL DEFAULT '[]'
  target_unit_index              INTEGER         NOT NULL
  unit_preview                   TEXT           
  answer                         TEXT           
  status                         TEXT            NOT NULL DEFAULT 'pending'
  asked_at                       TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  answered_at                    TEXT           
```
Row count: 3

### `classifications`
```
  id                             INTEGER         PRIMARY KEY
  email_id                       INTEGER         NOT NULL
  category                       TEXT            NOT NULL
  confidence                     REAL            NOT NULL
  reasoning                      TEXT           
  model                          TEXT            NOT NULL
  prompt_version                 INTEGER        
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 56

### `clients`
```
  id                             INTEGER         PRIMARY KEY
  email                          TEXT            NOT NULL
  name                           TEXT           
  organisation                   TEXT           
  country                        TEXT           
  is_vip                         INTEGER         NOT NULL DEFAULT 0
  notes                          TEXT           
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  updated_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 0

### `drafts`
```
  id                             INTEGER         PRIMARY KEY
  email_id                       INTEGER         NOT NULL
  parent_draft_id                INTEGER        
  subject                        TEXT            NOT NULL
  body                           TEXT            NOT NULL
  tone_notes                     TEXT           
  uses_signature                 INTEGER         NOT NULL DEFAULT 1
  sent_status                    TEXT            NOT NULL DEFAULT 'pending_approval'
  model                          TEXT            NOT NULL
  prompt_version                 INTEGER        
  reasoning                      TEXT           
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  updated_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  cognitive_state                TEXT            DEFAULT NULL
  voice_coverage_count           INTEGER         DEFAULT 0
```
Row count: 26

### `enrichments`
```
  id                             INTEGER         PRIMARY KEY
  email_id                       INTEGER         NOT NULL
  sender_name                    TEXT           
  sender_org                     TEXT           
  sender_country                 TEXT           
  likely_service_line            TEXT           
  urgency                        TEXT           
  routing_partner                TEXT           
  similar_memories               TEXT           
  client_match_id                INTEGER        
  summary                        TEXT           
  reasoning                      TEXT           
  model                          TEXT            NOT NULL
  prompt_version                 INTEGER        
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 18

### `firm_knowledge`
```
  id                             INTEGER         PRIMARY KEY
  key                            TEXT            NOT NULL
  value                          TEXT            NOT NULL
  category                       TEXT           
  updated_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 24

### `knowledge_library`
```
  id                             INTEGER         PRIMARY KEY
  kind                           TEXT            NOT NULL
  content                        TEXT            NOT NULL
  service_line                   TEXT           
  scope                          TEXT            NOT NULL DEFAULT 'universal'
  source_queue_id                INTEGER        
  confidence                     REAL            NOT NULL DEFAULT 1.0
  applied_count                  INTEGER         NOT NULL DEFAULT 0
  last_used_at                   TEXT           
  is_active                      INTEGER         NOT NULL DEFAULT 1
  created_by                     TEXT           
  deleted_by                     TEXT           
  deleted_at                     TEXT           
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  updated_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  purpose                        TEXT            DEFAULT 'voice_example'
  anika_proposed_purpose         TEXT            DEFAULT NULL
  anika_proposed_confidence      REAL            DEFAULT NULL
  anika_reasoning                TEXT            DEFAULT NULL
  user_confirmed_purpose         TEXT            DEFAULT NULL
  custom_purpose_label           TEXT            DEFAULT NULL
  is_custom_purpose              INTEGER         DEFAULT 0
```
Row count: 24

### `knowledge_library_vec_chunks`
```
  chunk_id                       INTEGER         PRIMARY KEY
  size                           INTEGER         NOT NULL
  validity                       BLOB            NOT NULL
  rowids                         BLOB            NOT NULL
```
Row count: 1

### `knowledge_library_vec_info`
```
  key                            TEXT            PRIMARY KEY
  value                          ANY            
```
Row count: 4

### `knowledge_library_vec_rowids`
```
  rowid                          INTEGER         PRIMARY KEY
  id                                            
  chunk_id                       INTEGER        
  chunk_offset                   INTEGER        
```
Row count: 25

### `knowledge_library_vec_vector_chunks00`
```
  rowid                                          PRIMARY KEY
  vectors                        BLOB            NOT NULL
```
Row count: 1

### `memory`
```
  id                             INTEGER         PRIMARY KEY
  kind                           TEXT            NOT NULL
  service_line                   TEXT           
  subject                        TEXT           
  content                        TEXT            NOT NULL
  source_email_id                INTEGER        
  source_draft_id                INTEGER        
  tags                           TEXT           
  embedding_model                TEXT            NOT NULL
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  is_active                      INTEGER         DEFAULT 1
```
Row count: 11

### `memory_vec_chunks`
```
  chunk_id                       INTEGER         PRIMARY KEY
  size                           INTEGER         NOT NULL
  validity                       BLOB            NOT NULL
  rowids                         BLOB            NOT NULL
```
Row count: 1

### `memory_vec_info`
```
  key                            TEXT            PRIMARY KEY
  value                          ANY            
```
Row count: 4

### `memory_vec_rowids`
```
  rowid                          INTEGER         PRIMARY KEY
  id                                            
  chunk_id                       INTEGER        
  chunk_offset                   INTEGER        
```
Row count: 11

### `memory_vec_vector_chunks00`
```
  rowid                                          PRIMARY KEY
  vectors                        BLOB            NOT NULL
```
Row count: 1

### `meta_rules`
```
  id                             INTEGER         PRIMARY KEY
  rule_text                      TEXT            NOT NULL
  trigger_pattern                TEXT           
  target_purpose                 TEXT            NOT NULL
  target_service_line            TEXT           
  priority                       INTEGER         DEFAULT 0
  is_active                      INTEGER         DEFAULT 1
  applied_count                  INTEGER         DEFAULT 0
  created_by                     TEXT            NOT NULL
  deleted_by                     TEXT           
  deleted_at                     TEXT           
  created_at                     TEXT            DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  updated_at                     TEXT            DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 0

### `raw_emails`
```
  id                             INTEGER         PRIMARY KEY
  gmail_message_id               TEXT            NOT NULL
  gmail_thread_id                TEXT            NOT NULL
  from_email                     TEXT            NOT NULL
  from_name                      TEXT           
  to_email                       TEXT            NOT NULL
  cc                             TEXT           
  subject                        TEXT           
  body_plain                     TEXT           
  body_html                      TEXT           
  snippet                        TEXT           
  received_at                    TEXT            NOT NULL
  is_reply_in_thread             INTEGER         NOT NULL DEFAULT 0
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  is_web_form                    INTEGER         NOT NULL DEFAULT 0
```
Row count: 79

### `reasoning_log`
```
  id                             INTEGER         PRIMARY KEY
  agent_name                     TEXT            NOT NULL
  email_id                       INTEGER        
  draft_id                       INTEGER        
  input_json                     TEXT            NOT NULL
  output_json                    TEXT           
  reasoning_text                 TEXT           
  model                          TEXT           
  prompt_version                 INTEGER        
  latency_ms                     INTEGER        
  status                         TEXT            NOT NULL DEFAULT 'ok'
  error_text                     TEXT           
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 1814

### `rules`
```
  id                             INTEGER         PRIMARY KEY
  rule_type                      TEXT            NOT NULL
  pattern                        TEXT           
  threshold_value                REAL           
  text_value                     TEXT           
  is_active                      INTEGER         NOT NULL DEFAULT 1
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 34

### `sent_log`
```
  id                             INTEGER         PRIMARY KEY
  draft_id                       INTEGER         NOT NULL
  email_id                       INTEGER         NOT NULL
  approval_id                    INTEGER         NOT NULL
  gmail_message_id               TEXT           
  gmail_thread_id                TEXT           
  to_email                       TEXT            NOT NULL
  subject                        TEXT            NOT NULL
  body                           TEXT            NOT NULL
  sent_at                        TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  test_mode                      INTEGER         NOT NULL DEFAULT 0
```
Row count: 1

### `system_state`
```
  key                            TEXT            PRIMARY KEY
  value                          TEXT            NOT NULL
  updated_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
```
Row count: 5

### `teaching_queue`
```
  id                             INTEGER         PRIMARY KEY
  raw_content                    TEXT            NOT NULL
  source_type                    TEXT            NOT NULL
  file_mime                      TEXT           
  original_filename              TEXT           
  stored_path                    TEXT           
  status                         TEXT            NOT NULL DEFAULT 'pending'
  error_text                     TEXT           
  created_by_user                TEXT            NOT NULL
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  processed_at                   TEXT           
  anika_proposed_purpose         TEXT            DEFAULT NULL
  anika_proposed_confidence      REAL            DEFAULT NULL
  anika_reasoning                TEXT            DEFAULT NULL
  anika_suggested_sl             TEXT            DEFAULT NULL
  anika_suggested_custom         TEXT            DEFAULT NULL
  humility_articulation          TEXT            DEFAULT NULL
  awaiting_confirmation          INTEGER         DEFAULT 1
```
Row count: 15

### `users`
```
  id                             INTEGER         PRIMARY KEY
  email                          TEXT            NOT NULL
  password_hash                  TEXT            NOT NULL
  role                           TEXT            NOT NULL
  created_at                     TEXT            NOT NULL DEFAULT strftime('%Y-%m-%dT%H:%M:%fZ','now')
  last_login_at                  TEXT           
```
Row count: 3


## 4. Schema Drift Analysis

Comparing live DB schema to `app/db/schema.sql`:

### Tables in live DB but NOT declared in schema.sql:
- `knowledge_library_vec_chunks`
- `knowledge_library_vec_info`
- `knowledge_library_vec_rowids`
- `knowledge_library_vec_vector_chunks00`
- `memory_vec_chunks`
- `memory_vec_info`
- `memory_vec_rowids`
- `memory_vec_vector_chunks00`
- `meta_rules`

### Column drift on key tables

#### `drafts`
- Columns added at runtime (not in schema.sql): `['cognitive_state', 'voice_coverage_count']`

#### `memory`
- Columns added at runtime (not in schema.sql): `['is_active']`

#### `knowledge_library`
- Columns added at runtime (not in schema.sql): `['anika_proposed_confidence', 'anika_proposed_purpose', 'anika_reasoning', 'custom_purpose_label', 'is_custom_purpose', 'purpose', 'user_confirmed_purpose']`
- Columns declared but missing in live DB: `['DEFAULT']`

#### `teaching_queue`
- Columns added at runtime (not in schema.sql): `['anika_proposed_confidence', 'anika_proposed_purpose', 'anika_reasoning', 'anika_suggested_custom', 'anika_suggested_sl', 'awaiting_confirmation', 'humility_articulation']`


## 5. Configuration

### `app/config/settings.py` — current settings:

```python
class Settings(BaseSettings):
    """Anika runtime settings sourced from `.env`.

    All fields mirror the keys in `.env.example`. Defaults are chosen to be
    safe for a first-boot laptop deployment.
    """

    # Gmail OAuth
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    prakasha_email: str = Field(default="prakasha@balakrishnaandco.com")
    approval_notify_email: str = Field(default="")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model_drafter: str = Field(default="gpt-4o")
    openai_model_classifier: str = Field(default="gpt-4o-mini")
    openai_model_enricher: str = Field(default="gpt-4o-mini")
    openai_model_learner: str = Field(default="gpt-4o-mini")
    openai_model_embedding: str = Field(default="text-embedding-3-small")

    # App
    anika_public_base_url: str = Field(default="http://localhost:8000")
    anika_host: str = Field(default="127.0.0.1")
    anika_port: int = Field(default=8000)

    gmail_poll_interval_seconds: int = Field(default=30)
    daily_send_cap: int = Field(default=30)
    undo_window_seconds: int = Field(default=10)

    anika_test_mode: bool = Field(default=False)
    anika_tz: str = Field(default="Asia/Kolkata")

    # Auth — session cookie signing + first-boot user seed.
    # Why a separate secret: we never want .env leakage to unlock existing sessions.
    # Rotate this (and restart) to invalidate every session at once.
    session_secret: str = Field(default="change-me-in-production-please")
    session_max_age_days: int = Field(default=7)
    # If True, the session cookie has the Secure flag (HTTPS only). Set to False
    # during localhost pilot; flip to True once Cloudflare Tunnel/TLS is in place.
    session_cookie_secure: bool = Field(default=False)

    # First-boot seeding of the two default users. If empty, random passwords
    # are generated and printed once to the console.
    ak_email: str = Field(default="aks@marketiqx.com")
    ak_initial_password: str = Field(default="")
    prakasha_initial_password: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Paths — plain Python properties (not computed_field) so tests can subclass + override.
    # Why not pydantic fields: we don't want them settable from env; they're derived from the
    # project root, which is constant in production and needs to be redirectable in tests.

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        return PROJECT_ROOT / "anika.db"

    @property
    def token_path(self) -> Path:
        """Absolute path to the Gmail OAuth token JSON (created on first run)."""
        return PROJECT_ROOT / "token.json"

    @property
    def credentials_path(self) -> Path:
        """Path to an optional credentials.json (preferred by Google's
```

### `system_state` table — runtime feature flags:

```
  daily_sent_count: 1
  daily_sent_date: 2026-04-23
  drafting_paused: off
  kill_switch: off
  last_gmail_history_id: 
```

## 6. Agents Inventory

All agent files and their public functions / classes:

### `app/agents/approver.py`
- File size: 9822 chars
- Public functions: `async approve()`, `async edit()`, `reject()`

### `app/agents/classifier.py`
- File size: 4763 chars
- Public functions: `async classify()`
- max_turns: 2

### `app/agents/drafter.py`
- File size: 13754 chars
- Public functions: `assemble_prompt()`, `async draft_reply()`
- max_turns: 16
- Tools: `tool_get_signature_block`, `tool_get_tone_rules`, `tool_get_firm_fact`, `tool_get_faq_answers`, `tool_retrieve_similar_drafts`, `tool_retrieve_firm_snippets`, `tool_get_routing_partner`

### `app/agents/duplicate_judge.py`
- File size: 6843 chars
- Classes: `DuplicateJudgment`
- Public functions: `async judge_duplicate()`
- max_turns: 3

### `app/agents/enricher.py`
- File size: 9241 chars
- Public functions: `async enrich()`
- max_turns: 20
- Tools: `tool_lookup_client`, `tool_retrieve_similar_drafts`, `tool_retrieve_firm_snippets`, `tool_get_routing_partner`

### `app/agents/humility_layer.py`
- File size: 6588 chars
- Classes: `UnknownArticulation`
- Public functions: `async articulate_uncertainty()`
- max_turns: 3

### `app/agents/learner.py`
- File size: 651 chars

### `app/agents/meta_rule_generator.py`
- File size: 6440 chars
- Classes: `MetaRuleProposal`
- Public functions: `async generate_meta_rule()`
- max_turns: 3

### `app/agents/orchestrator.py`
- File size: 12587 chars
- Public functions: `ingest_message()`, `async handle()`

### `app/agents/purpose_classifier.py`
- File size: 7897 chars
- Classes: `PurposeProposal`
- Public functions: `async classify_purpose()`
- max_turns: 3

### `app/agents/schemas.py`
- File size: 2603 chars
- Classes: `ClassifierOutput`, `EnricherOutput`, `DrafterOutput`, `LearnerOutput`

### `app/agents/sender.py`
- File size: 5818 chars
- Classes: `SendRefused`
- Public functions: `async send_approved_draft()`

### `app/agents/teaching_learner.py`
- File size: 9197 chars
- Classes: `LearnerUnit`, `LearnerClarification`, `LearnerOutput`
- Public functions: `adaptive_clarification_limit()`, `detect_pii_in_unit()`, `async extract()`, `cap_clarifications()`
- max_turns: 4

### `app/agents/tools_sdk.py`
- File size: 3162 chars
- Public functions: `tool_get_firm_fact()`, `tool_get_signature_block()`, `tool_get_tone_rules()`, `tool_get_faq_answers()`, `tool_get_routing_partner()`, `tool_retrieve_similar_drafts()`, `tool_retrieve_firm_snippets()`, `tool_lookup_client()`


## 7. Routes Inventory

All HTTP endpoints registered in `app/dashboard/routes.py`:

```
  GET    /healthz                                 -> healthz()
  GET    /", response_class=HTMLResponse          -> root()
  GET    /drafts", response_class=HTMLResponse    -> drafts_index()
  GET    /drafts/{draft_id}", response_class=HTMLResponse -> draft_detail()
  POST   /drafts/{draft_id}/approve               -> draft_approve()
  POST   /drafts/{draft_id}/edit                  -> draft_edit()
  POST   /drafts/{draft_id}/reject                -> draft_reject()
  GET    /inbox", response_class=HTMLResponse     -> inbox_index()
  GET    /inbox/{email_id}", response_class=HTMLResponse -> inbox_detail()
  GET    /train", response_class=HTMLResponse     -> train_index()
  POST   /train/teach                             -> train_teach()
  POST   /train/teach/confirm                     -> train_teach_confirm()
  GET    /train/review-rule/{queue_id}", response_class=HTMLResponse -> train_review_rule()
  POST   /train/review-rule/{queue_id}/decide     -> train_review_rule_decide()
  POST   /train/clarify/{clar_id}                 -> train_clarify()
  POST   /train/library/{entry_id}/edit           -> train_library_edit()
  POST   /train/library/{entry_id}/delete         -> train_library_delete()
  GET    /train/library/export                    -> train_library_export()
  POST   /settings/drafting_paused                -> toggle_drafting_paused()
  DELETE /settings/signature                      -> signature_is_locked()
  GET    /train/rules", response_class=HTMLResponse -> train_rules_list()
  GET    /train/rules/new", response_class=HTMLResponse -> train_rules_new_form()
  GET    /train/rules/{rule_id}/edit", response_class=HTMLResponse -> train_rules_edit_form()
  POST   /train/rules/save                        -> train_rules_save()
  POST   /train/rules/{rule_id}/delete            -> train_rules_delete()
  GET    /teaching-dashboard", response_class=HTMLResponse -> teaching_dashboard()
  GET    /knowledge-graph", response_class=HTMLResponse -> knowledge_graph()
  GET    /analytics", response_class=HTMLResponse -> analytics()
  GET    /settings", response_class=HTMLResponse  -> settings_index()
  POST   /settings/kill_switch                    -> toggle_kill_switch()
  POST   /settings/clients/add                    -> add_client()
  POST   /settings/clients/{client_id}/vip        -> toggle_vip()
  POST   /settings/clients/{client_id}/delete     -> delete_client()
  POST   /settings/backfill_memory                -> run_backfill_memory_with_vectors()
  POST   /settings/poll_now                       -> trigger_poll_now()
  GET    /settings/gmail/connect                  -> gmail_connect_start()
  GET    /settings/audit", response_class=HTMLResponse -> settings_audit()
```

## 8. Knowledge Library State

- Active entries: 23
- Soft-deleted entries: 1

### Active entries by purpose:

```
  reference_material        : 10
  firm_policy               : 3
  firm_fact                 : 3
  document_type             : 3
  classifier_example        : 2
  workflow_rule             : 1
  voice_example             : 1
```

### Active entries by service_line:

```
  NULL                      : 18
  nri_tax                   : 3
  foreign_subsidiary        : 1
  audit                     : 1
```

### All voice_examples (full content):

- **id=25** | nri_tax | by `prakasha` | applied 3x
  - preview: Dear Vijay,

Thank you for reaching out regarding tax consultation for your return to India.

We will be glad to assist you with planning your tax matters, including determination of residential statu


## 9. Memory Table State (legacy / deprecated patterns)

- Total rows: 11
- Active: 7, Deactivated: 4

```
  ON  id=  1 | firm_snippet    | -                    | Track record for foreign companies
  ON  id=  2 | firm_snippet    | -                    | Track record for NRIs
  ON  id=  3 | firm_snippet    | -                    | MSI Global Alliance membership
  ON  id=  4 | firm_snippet    | -                    | Partner expertise — Kumar Prasad
  ON  id=  5 | firm_snippet    | -                    | Partner expertise — Prakasha
  OFF id=  6 | exemplar        | foreign_subsidiary   | Setting up India subsidiary — happy to s
  OFF id=  7 | exemplar        | nri_tax              | NRI ITR for last year — happy to guide
  OFF id=  8 | exemplar        | transfer_pricing     | Transfer pricing study — happy to scope
  OFF id=  9 | exemplar        | virtual_cfo          | Virtual CFO for your startup — happy to 
  ON  id= 10 | firm_snippet    | -                    | 
  ON  id= 11 | approved_draft  | nri_tax              | Re: Your enquiry to Balakrishna & Co
```

## 10. Drafts State

- Total drafts: 26

### By status:

```
  rejected                  : 13
  edited                    : 6
  pending_approval          : 6
  sent                      : 1
```

### Last 10 drafts (chronological):

```
  id   status                 cog_state    vcc   service_line           from                          
    30 pending_approval       learning     1     nri_tax                venkatalachareddyperam@gmail.c
    29 pending_approval       learning     1     nri_tax                vikatakavi.divya@gmail.com
    28 pending_approval       cold_start   0     transfer_pricing       ramesh1333@gmail.com
    27 rejected               cold_start   0     other                  hemajenne722@gmail.com
    26 pending_approval       cold_start   0     secretarial_roc        atulyaharshwardhan@gmail.com
    25 pending_approval       cold_start   0     foreign_subsidiary     manglamconsultancy9@gmail.com
    24 pending_approval       learning     1     nri_tax                vijayr113@gmail.com
    23 edited                 -            0     nri_tax                vijayr113@gmail.com
    22 sent                   -            0     nri_tax                chandrika.share@gmail.com
    21 edited                 -            0     nri_tax                chandrika.share@gmail.com
```

## 11. Test Suite Status

Re-run from outer shell after subprocess.run path-resolution failure inside the audit script:

```
13 failed, 118 passed in 41.76s
```

### Failing tests:
- tests/test_agents_offline.py::test_vip_sender_bypasses_drafter
- tests/test_auth.py::test_user_role_can_access_train
- tests/test_auth.py::test_admin_can_access_train_and_analytics
- tests/test_drafter_assembly.py::test_assemble_prompt_always_ends_with_signature_instruction
- tests/test_drafter_assembly.py::test_assemble_prompt_pulls_universal_and_service_rules
- tests/test_drafter_assembly.py::test_assemble_prompt_retrieves_examples_via_embedding
- tests/test_drafter_assembly.py::test_retrieve_rules_skips_inactive_entries
- tests/test_drafter_assembly.py::test_retrieve_rules_returns_only_matching_service_line
- tests/test_train_routes.py::test_train_visible_to_user_role
- tests/test_train_routes.py::test_post_teach_text_creates_queue_and_library
- tests/test_train_routes.py::test_post_teach_file_creates_queue_row
- tests/test_train_routes.py::test_admin_sees_prompt_preview_link
- tests/test_train_routes.py::test_drafting_paused_short_circuits_orchestrator

### Failure clusters (root causes, not 13 different bugs):
1. **Schema-drift errors** (`sqlite3.OperationalError: no such column: anika_proposed_purpose`) — `/train` route SQL references columns that exist in the LIVE anika.db but not in tests'`init_db()` build because they were never added to schema.sql. Hits any test that GETs /train.
2. **`retrieve_rules` SQL filters on `purpose`** — same root cause; a column that exists in live DB but not in the test-fresh schema. Affects 5 drafter_assembly tests.
3. **VIP bypass test mismatch** — `structural_validator` was added as gate #5 BEFORE the VIP gate fires; test asserts the old `bypass_vip` action but now structural_validator catches the message first.
4. **drafting_paused short-circuit test** — same: structural_validator now intercepts before drafting_paused even runs.
5. **`tests/test_auth.py::test_admin_can_access_train_and_analytics`** — same column-not-found error.

These 13 failures are blocked by **two** real fixes:
  - Get schema.sql + init_db() back in sync with live DB columns (`anika_proposed_*`, `purpose`, `is_custom_purpose`, `custom_purpose_label`, `user_confirmed_purpose`, `anika_reasoning` on knowledge_library; same suffix on teaching_queue; `humility_articulation` and `awaiting_confirmation` on teaching_queue; `is_active` on memory; `cognitive_state` and `voice_coverage_count` on drafts).
  - Update 2 tests for the new structural_validator gate ordering.

Exit code: 1
FAIL

## 12. Known Outstanding State

This section was originally written from PowerShell-debug-session memory, not
from verified execution. Cluster 1 of the Phase 1B stabilization sprint
re-classified each claim as VERIFIED, FALSE, or UNVERIFIED (will be confirmed
or refuted by subsequent clusters).

### Verified by Cluster 1 probes (2026-04-26)

- VERIFIED -- Drafter health: 30/30 reasoning_log rows have status='ok'. Zero
  MaxTurnsExceeded, zero embed/API failures recorded against the Drafter. The
  max_turns=16 ceiling is healthy.
- VERIFIED -- Sent draft 22 (Chandrika): clean canonical signature.
  "Yours faithfully," count = 1, "CA Prakasha" count = 1. No legacy
  "Warm regards" / "S V Prakasha" / "Wilson Garden" artefacts. Matches the
  locked firm_identity.SIGNATURE_BLOCK exactly.
- VERIFIED (Cluster 6 retraction) -- Earlier Cluster 1 claim of "2 mojibake
  characters in sent draft 22" was a FALSE POSITIVE. Cluster 6 inspected
  the actual stored bytes: positions 184 and 274 in drafts.body contain
  valid U+2014 em-dashes ("—") in correct UTF-8. The "\ufffd" glyphs in the
  Cluster 1 stdout were the Windows-Bash terminal failing to render U+2014
  with its active code page — a display-side artefact, not data corruption.
  The sent email reached Chandrika with proper em-dashes intact. No fix
  needed in the email pipeline.
- VERIFIED (Cluster 7) -- vec orphan cleanup. knowledge_library_vec_rowids
  had 25 entries while knowledge_library had 24 rows (any state). The diff
  was a true orphan at vec rowid=3 (no matching library row at any
  is_active state) — hard-deleted in Cluster 7. The dormant pairing for
  vec rowid=24 (its library row is soft-deleted, deleted_by=aks) was
  KEPT by design: retrieve_examples() filters is_active=1, so the
  vector is unreachable today, but if AK ever un-deletes the library
  row, the embedding is still present. Final state: 24 vec rows ↔ 24
  library rows, 1:1, zero orphans.
- FALSE -- "Enricher refactored to tool-less". The current `_build_agent` in
  app/agents/enricher.py still passes tools=[tool_lookup_client,
  tool_retrieve_similar_drafts, tool_retrieve_firm_snippets,
  tool_get_routing_partner]. max_turns=20. The refactor was DESIGNED
  during the weekend session but NEVER EXECUTED -- the file was not actually
  edited. Cluster 4 of this stabilization will land it for real, with a
  verification step on the Sumana stuck-email case (Cluster 5).
- FALSE -- "Enricher INSTRUCTIONS rewritten to consume PRE-FETCHED CONTEXT".
  Same root cause: never executed. Will land in Cluster 4.
- VERIFIED (corollary) -- enrich() does include a try/except for
  MaxTurnsExceeded with heuristic fallback. This was kept and remains as
  defense-in-depth even after Cluster 4 lands the tool-less refactor.

### UNVERIFIED claims from the original Section 12

These need execution-level verification before being trusted. The
stabilization sprint will not treat any of these as ground truth without a
probe:

- UNVERIFIED -- Recruitment + vendor_pitch added to Category Literal in
  app/agents/schemas.py. (Section 6 inventory shows schemas.py was modified
  -- but content not yet probed.)
- UNVERIFIED -- Classifier INSTRUCTIONS extended to recognize new categories.
- UNVERIFIED -- Orchestrator dispatch now auto-skips recruitment/vendor with
  audit reason.
- UNVERIFIED -- notify_tool.notify_draft_ready patched to read
  cognitive_state from drafts and prepend honesty preamble; legacy
  notify_sensitive_bypass restored.
- UNVERIFIED -- firm_knowledge.signature_block row deleted from DB.
- UNVERIFIED -- backfill_memory.py FIRM_FACTS list had signature_block entry
  removed.
- UNVERIFIED -- knowledge_tool.get_signature_block() rewritten to return
  firm_identity.SIGNATURE_BLOCK.
- UNVERIFIED -- memory table: rows id=6,7,8,9 marked is_active = 0.
- UNVERIFIED -- memory_tool.semantic_search filters is_active = 0 rows.
- UNVERIFIED -- library.voice_coverage() helper exists in
  app/cognitive/library.py.
- UNVERIFIED -- Drafter assemble_prompt() returns 3-tuple (prompt, used_ids,
  coverage).
- UNVERIFIED -- Drafter draft_reply() detects enrichment_was_fallback and
  appends partial-enrichment warning.
- UNVERIFIED -- draft_detail.html cognitive humility banner present.
- UNVERIFIED -- app/auth/middleware.py PageVisitLoggerMiddleware added AND
  registered in app/main.py.
- UNVERIFIED -- _save_as_voice_example() strips signature markers before
  saving.
- UNVERIFIED -- Library id=25 was signature-stripped manually.
- UNVERIFIED -- Draft 27 was rejected with audit reason.
- UNVERIFIED -- Draft 25 was manually signature-cleaned.

### Schema-state facts confirmed by Section 3 of this audit

(Section 3 PRAGMA dump is the authoritative source for current table shape.)

- VERIFIED -- drafts table has cognitive_state (TEXT, default NULL) and
  voice_coverage_count (INTEGER, default 0).
- VERIFIED -- memory table has is_active (INTEGER, default 1).
- VERIFIED -- meta_rules table exists (0 rows).
- VERIFIED -- users table has prasad@balakrishnaandco.com (3 user rows total
  per Section 3 row-count: aks, prakasha, prasad).
- DEFECT (covered by Cluster 2) -- None of the above schema additions are
  declared in app/db/schema.sql. They were added via runtime ALTER TABLE in
  the 174 untracked debug scripts at project root.

### Files NOT yet created -- confirmed by filesystem inspection

- VERIFIED -- app/agents/critic_rules.py does not exist.
- VERIFIED -- app/agents/critic.py does not exist.
- VERIFIED -- app/llm.py does not exist.
- VERIFIED -- app/embeddings.py does not exist.

These remain Phase 1C targets.

### Items deferred to Phase 1C / 1D / 2

- LLM abstraction layer (app/llm.py)
- Embeddings abstraction (app/embeddings.py)
- Critic agent (rule-based + LLM hybrid)
- Pattern recognition (B1)
- Self-audit narrative (B3)
- Per-partner data isolation (Phase 1C)
- Local LLM migration (Phase 2 sovereignty)
- Calendar integration
- Thread reply support
- Document intake
- Edit-distance trending dashboard
