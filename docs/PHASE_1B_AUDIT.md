# Phase 1B Stabilization Audit

Generated: 2026-04-26 11:34:16 UTC

## 1. Git State

- Current branch: `master`
- Current commit: `eddbc66` (eddbc66e6c8c2ecf52104158991a94696dcc8a27)
- Last tag: `phase-1a-complete`
- All tags: `phase-1a-complete
pre-learner-refactor`
- Uncommitted changes: 229

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
 M app/db/connection.py
 M app/db/schema.sql
 M app/jobs/backfill_memory.py
 M app/main.py
 M app/tools/gmail_tool.py
 M app/tools/knowledge_tool.py
 M app/tools/notify_tool.py
R  bump.py -> scripts/debug-archive/bump.py
RM check.py -> scripts/debug-archive/check.py
R  check_draft.py -> scripts/debug-archive/check_draft.py
R  clean_partner.py -> scripts/debug-archive/clean_partner.py
RM cleanup.py -> scripts/debug-archive/cleanup.py
R  crosscheck.py -> scripts/debug-archive/crosscheck.py
R  diag2.py -> scripts/debug-archive/diag2.py
R  diag3.py -> scripts/debug-archive/diag3.py
R  diag4.py -> scripts/debug-archive/diag4.py
... (199 more)
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
- ` M app/db/connection.py`
- ` M app/db/schema.sql`
- ` M app/jobs/backfill_memory.py`
- ` M app/main.py`
- ` M app/tools/gmail_tool.py`
- ` M app/tools/knowledge_tool.py`
- ` M app/tools/notify_tool.py`
- `R  bump.py -> scripts/debug-archive/bump.py`
- `RM check.py -> scripts/debug-archive/check.py`
- `R  check_draft.py -> scripts/debug-archive/check_draft.py`
- `R  clean_partner.py -> scripts/debug-archive/clean_partner.py`
- `RM cleanup.py -> scripts/debug-archive/cleanup.py`
- `R  crosscheck.py -> scripts/debug-archive/crosscheck.py`
- `R  diag2.py -> scripts/debug-archive/diag2.py`
- `R  diag3.py -> scripts/debug-archive/diag3.py`
- `R  diag4.py -> scripts/debug-archive/diag4.py`
- `R  diag6.py -> scripts/debug-archive/diag6.py`
- `R  diag7.py -> scripts/debug-archive/diag7.py`
- `R  find_chandrika.py -> scripts/debug-archive/find_chandrika.py`
- `R  find_web.py -> scripts/debug-archive/find_web.py`
- `R  fix_draft22.py -> scripts/debug-archive/fix_draft22.py`
- `R  get_chandrika.py -> scripts/debug-archive/get_chandrika.py`
- `R  resetpw.py -> scripts/debug-archive/resetpw.py`
- `R  show_drafter.py -> scripts/debug-archive/show_drafter.py`
- `R  trim.py -> scripts/debug-archive/trim.py`
- `R  verify.py -> scripts/debug-archive/verify.py`
- ` M tests/test_agents_offline.py`
- ` M tests/test_drafter_assembly.py`
- ` M tests/test_train_routes.py`
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
- `?? docs/PHASE_1B_AUDIT.before-stabilization.md`
- `?? docs/PHASE_1B_AUDIT.md`
- `?? scripts/debug-archive/README.md`
- `?? scripts/debug-archive/adaptation_audit.py`
- `?? scripts/debug-archive/add_dashboard_route.py`
- `?? scripts/debug-archive/add_finalize_with_purpose.py`
- `?? scripts/debug-archive/add_graph_route.py`
- `?? scripts/debug-archive/add_page_visit.py`
- `?? scripts/debug-archive/add_progress_tab.py`
- `?? scripts/debug-archive/add_progress_tab_v2.py`
- `?? scripts/debug-archive/add_rules_nav.py`
- `?? scripts/debug-archive/add_rules_routes.py`
- `?? scripts/debug-archive/add_visit_logger.py`
- `?? scripts/debug-archive/audit_gmail_writes.py`
- `?? scripts/debug-archive/audit_legacy_rules.py`
- `?? scripts/debug-archive/audit_prakasha.py`
- `?? scripts/debug-archive/audit_signature_drift.py`
- `?? scripts/debug-archive/audit_uncertainty.py`
- `?? scripts/debug-archive/backfill_state.py`
- `?? scripts/debug-archive/build_validator.py`
- `?? scripts/debug-archive/check_876.py`
- `?? scripts/debug-archive/check_activity.py`
- `?? scripts/debug-archive/check_both.py`
- `?? scripts/debug-archive/check_draft25_sigs.py`
- `?? scripts/debug-archive/check_drafts.py`
- `?? scripts/debug-archive/check_his_edits.py`
- `?? scripts/debug-archive/check_prakasha_activity.py`
- `?? scripts/debug-archive/check_prasad.py`
- `?? scripts/debug-archive/check_preview.py`
- `?? scripts/debug-archive/check_queue.py`
- `?? scripts/debug-archive/check_retrieve_rules.py`
- `?? scripts/debug-archive/clean_orphan.py`
- `?? scripts/debug-archive/cleanup_db.py`
- `?? scripts/debug-archive/cleanup_inbox.py`
- `?? scripts/debug-archive/cleanup_noise.py`
- `?? scripts/debug-archive/close_stale_clarifications.py`
- `?? scripts/debug-archive/create_prasad.py`
- `?? scripts/debug-archive/deep_diagnose_sumana.py`
- `?? scripts/debug-archive/diag.py`
- `?? scripts/debug-archive/diag_banner.py`
- `?? scripts/debug-archive/diag_double_sig.py`
- `?? scripts/debug-archive/diag_enricher.py`
- `?? scripts/debug-archive/diag_finalize.py`
- `?? scripts/debug-archive/diag_learner.py`
- `?? scripts/debug-archive/diag_skip.py`
- `?? scripts/debug-archive/engagement_report.py`
- `?? scripts/debug-archive/find_answer_clar.py`
- `?? scripts/debug-archive/find_callers.py`
- `?? scripts/debug-archive/find_inbox.py`
- `?? scripts/debug-archive/find_insert.py`
- `?? scripts/debug-archive/find_notification.py`
- `?? scripts/debug-archive/find_prompt.py`
- `?? scripts/debug-archive/fix_active_tab.py`
- `?? scripts/debug-archive/fix_attribution.py`
- `?? scripts/debug-archive/fix_banner.py`
- `?? scripts/debug-archive/fix_draft25.py`
- `?? scripts/debug-archive/fix_endif.py`
- `?? scripts/debug-archive/fix_enricher.py`
- `?? scripts/debug-archive/fix_humility_v2.py`
- `?? scripts/debug-archive/fix_last_retrieve.py`
- `?? scripts/debug-archive/fix_notify_restore.py`
- `?? scripts/debug-archive/fix_queue_12.py`
- `?? scripts/debug-archive/fix_signature_root.py`
- `?? scripts/debug-archive/fix_skip_path.py`
- `?? scripts/debug-archive/fix_status_constraint.py`
- `?? scripts/debug-archive/full_diag.py`
- `?? scripts/debug-archive/inspect_classifier.py`
- `?? scripts/debug-archive/inspect_dispatch.py`
- `?? scripts/debug-archive/inspect_middleware.py`
- `?? scripts/debug-archive/inspect_msg_type.py`
- `?? scripts/debug-archive/investigate_leak.py`
- `?? scripts/debug-archive/investigate_learner.py`
- `?? scripts/debug-archive/investigate_quality.py`
- `?? scripts/debug-archive/learning_check.py`
- `?? scripts/debug-archive/live_tracker.py`
- `?? scripts/debug-archive/make_dashboard_template.py`
- `?? scripts/debug-archive/make_graph_template.py`
- `?? scripts/debug-archive/make_rule_form_template.py`
- `?? scripts/debug-archive/make_rules_template.py`
- `?? scripts/debug-archive/monitor_prakasha.py`
- `?? scripts/debug-archive/morning_check.py`
- `?? scripts/debug-archive/partner_activity.py`
- `?? scripts/debug-archive/patch_answer.py`
- `?? scripts/debug-archive/patch_clarification_ui.py`
- `?? scripts/debug-archive/patch_dedup.py`
- `?? scripts/debug-archive/patch_fallback.py`
- `?? scripts/debug-archive/patch_filter.py`
- `?? scripts/debug-archive/patch_gmail_v2.py`
- `?? scripts/debug-archive/patch_inbox_strict.py`
- `?? scripts/debug-archive/patch_inbox_view.py`
- `?? scripts/debug-archive/patch_learner.py`
- `?? scripts/debug-archive/patch_notify.py`
- `?? scripts/debug-archive/patch_notify_v2.py`
- `?? scripts/debug-archive/patch_notify_v3.py`
- `?? scripts/debug-archive/patch_orch_gate.py`
- `?? scripts/debug-archive/patch_orch_step1.py`
- `?? scripts/debug-archive/patch_recruitment_filter.py`
- `?? scripts/debug-archive/patch_save_stripping.py`
- `?? scripts/debug-archive/patch_unknown.py`
- `?? scripts/debug-archive/patch_voice_save.py`
- `?? scripts/debug-archive/prakasha_activity.py`
- `?? scripts/debug-archive/prasad_journey.py`
- `?? scripts/debug-archive/prasad_now.py`
- `?? scripts/debug-archive/promote.py`
- `?? scripts/debug-archive/promote2.py`
- `?? scripts/debug-archive/qc_mangalam.py`
- `?? scripts/debug-archive/qc_report.py`
- `?? scripts/debug-archive/quick_check.py`
- `?? scripts/debug-archive/real_adaptation_check.py`
- `?? scripts/debug-archive/reject_27.py`
- `?? scripts/debug-archive/reset_ak.py`
- `?? scripts/debug-archive/restore.py`
- `?? scripts/debug-archive/retest_humility.py`
- `?? scripts/debug-archive/retry_atulya_safe.py`
- `?? scripts/debug-archive/retry_atulya_v2.py`
- `?? scripts/debug-archive/retry_atulya_v3.py`
- `?? scripts/debug-archive/root_cause.py`
- `?? scripts/debug-archive/see_damage.py`
- `?? scripts/debug-archive/see_dispatch.py`
- `?? scripts/debug-archive/see_notify_now.py`
- `?? scripts/debug-archive/see_sumana.py`
- `?? scripts/debug-archive/show_draft_detail.py`
- `?? scripts/debug-archive/show_file_flow.py`
- `?? scripts/debug-archive/show_finalize.py`
- `?? scripts/debug-archive/show_learning_engine.py`
- `?? scripts/debug-archive/show_memory_tool.py`
- `?? scripts/debug-archive/show_meta_rules_schema.py`
- `?? scripts/debug-archive/show_notify.py`
- `?? scripts/debug-archive/show_retrieve.py`
- `?? scripts/debug-archive/show_semantic_search.py`
- `?? scripts/debug-archive/show_teach_route.py`
- `?? scripts/debug-archive/sim.py`
- `?? scripts/debug-archive/stabilization_audit.py`
- `?? scripts/debug-archive/state_check.py`
- `?? scripts/debug-archive/step1_schema.py`
- `?? scripts/debug-archive/step2_helper.py`
- `?? scripts/debug-archive/step3a_drafter_prompt.py`
- `?? scripts/debug-archive/step3b_caller.py`
- `?? scripts/debug-archive/step3b_fix.py`
- `?? scripts/debug-archive/step4_insert.py`
- `?? scripts/debug-archive/step5_banner.py`
- `?? scripts/debug-archive/step6_deactivate_legacy.py`
- `?? scripts/debug-archive/strip_lib_sig.py`
- `?? scripts/debug-archive/strip_old_sigs.py`
- `?? scripts/debug-archive/task1_add_purpose.py`
- `?? scripts/debug-archive/task2_classification_columns.py`
- `?? scripts/debug-archive/task3_custom_label.py`
- `?? scripts/debug-archive/task4_meta_rules.py`
- `?? scripts/debug-archive/task5_migrate.py`
- `?? scripts/debug-archive/task6_classifier.py`
- `?? scripts/debug-archive/task7a_meta_gen.py`
- `?? scripts/debug-archive/task7b_step1.py`
- `?? scripts/debug-archive/task7b_step2.py`
- `?? scripts/debug-archive/task7b_step3.py`
- `?? scripts/debug-archive/task7b_step4.py`
- `?? scripts/debug-archive/task7b_step5.py`
- `?? scripts/debug-archive/task9_drafter_filter.py`
- `?? scripts/debug-archive/test_classifier.py`
- `?? scripts/debug-archive/test_dedup.py`
- `?? scripts/debug-archive/test_humility.py`
- `?? scripts/debug-archive/test_meta_rules.py`
- `?? scripts/debug-archive/test_voice_save.py`
- `?? scripts/debug-archive/time_check.py`
- `?? scripts/debug-archive/trace_callers.py`
- `?? scripts/debug-archive/trace_signature.py`
- `?? scripts/debug-archive/triage.py`
- `?? scripts/debug-archive/update_confirm_route.py`
- `?? scripts/debug-archive/verify_clean_sig.py`
- `?? scripts/debug-archive/verify_confirm.py`
- `?? scripts/debug-archive/verify_draft26.py`
- `?? scripts/debug-archive/verify_drafter_filter.py`
- `?? scripts/debug-archive/verify_restore.py`
- `?? scripts/debug-archive/verify_skip.py`
- `?? scripts/debug-archive/visits.py`
- `?? scripts/debug-archive/watch.py`
- `?? scripts/debug-archive/who_loggedin.py`

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
Row count: 208

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
Row count: 24

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
Row count: 1815

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

Tables: aligned.

### Column drift on key tables


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
- File size: 10886 chars
- Public functions: `async enrich()`
- max_turns: 3
- Tools: tool-less

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

Running full pytest suite (this may take 1-2 min)...

```
........................................................................ [ 54%]
...........................................................              [100%]
```

Exit code: 0
PASS

## 12. Known Outstanding State

This audit is the post-stabilization baseline (Phase 1B → 1C handover).
Every claim in this section is verified against the live codebase or DB by
the audit harness above (Sections 1-11) or by an explicit Cluster probe in
the Phase 1B stabilization sprint.

### Verified by Phase 1B stabilization sprint

- VERIFIED — Drafter health: every reasoning_log row for agent_name='drafter'
  has status='ok'. No MaxTurnsExceeded or embed/API failures recorded.
- VERIFIED — Sent draft 22 (Chandrika) carries a single canonical signature
  matching app/config/firm_identity.SIGNATURE_BLOCK. The Cluster 1 'mojibake
  defect' was retracted in Cluster 6: it was a Windows-Bash terminal failing
  to render U+2014 em-dashes, not data corruption.
- VERIFIED — Enricher refactored to tool-less in Cluster 4. The Agent()
  constructor no longer receives tools=[...]; lookup_client +
  retrieve_similar_drafts are pre-fetched in enrich() and inlined as
  PRE-FETCHED CONTEXT in the user_input. max_turns dropped 20 → 3.
  The MaxTurnsExceeded fallback is preserved as defense-in-depth.
- VERIFIED — Cluster 5 retried email 877 (Sumana, the previously-stuck enquiry)
  through the new tool-less Enricher: completed in 8.12s, no MaxTurnsExceeded,
  classified as nri_tax (correct — UK-NRI tax question). reasoning_log row
  contains 'pre_fetched_context' + 'tool_less'=True. Probe forensic ID in
  reasoning_log; duplicate enrichments row was cleaned up.
- VERIFIED — Cluster 2 promoted every runtime-added column into
  app/db/schema.sql + matching _ensure_column migrations in init_db().
  A fresh DB built from schema.sql now matches live anika.db column-for-
  column, attribute-for-attribute, in declaration order (PRAGMA parity).
  Section 4 above confirms 'Tables: aligned.'
- VERIFIED — Cluster 7 cleaned up the orphan vec row (knowledge_library_vec
  rowid=3 with no matching library row at any is_active state). Final state:
  24 vec rows ↔ 24 library rows, 1:1, zero orphans. The dormant vec for
  vec rowid=24 (its library row is soft-deleted, deleted_by=aks) was kept by
  design — retrieve_examples() filters is_active=1 anyway.
- VERIFIED — Cluster 8 archived 192 scratch debug scripts from the project
  root into scripts/debug-archive/ (forensic value preserved, working tree
  readable). The directory is git-tracked, NOT in .gitignore.
- VERIFIED — Cluster 9: full pytest suite reports 131 passed, 0 failed,
  0 warnings (Section 11 above is the live re-run).

### Files deliberately NOT yet created — Phase 1C targets

- `app/llm.py` — provider-agnostic LLM abstraction
- `app/embeddings.py` — provider-agnostic embeddings abstraction
- `app/agents/critic.py` + `app/agents/critic_rules.py` — critic agent
  (rule-based + LLM hybrid)

### Items deferred to Phase 1C / 1D / 2

- Pattern recognition (B1)
- Self-audit narrative (B3)
- Per-partner data isolation (Phase 1C)
- Local LLM migration (Phase 2 sovereignty)
- Calendar integration
- Thread reply support
- Document intake
- Edit-distance trending dashboard