# Anika — Technical Architecture (v2, Laptop deployment)

**Version:** 2.0
**Supersedes:** v1.0 (which used Railway + Supabase)
**Deployment:** Windows laptop (pilot) → old laptop/VPS (production after Week 2)

---

## 1. Deployment model

Anika runs as a Python service on AK's Windows laptop for the first 7-14 days. Data stored locally in SQLite. After production validation, migrate to dedicated hardware.

**Why this approach:** Prakash sir's data never touches third-party managed services during the pilot. Data stays under AK's physical control. Builds trust through operational transparency, not through architectural compromise.

## 2. The six agents (fully agentic, OpenAI Agents SDK)

1. **Anika (orchestrator)** — Receives each email, decides the workflow, calls sub-agents as tools
2. **Classifier** — GPT-4o-mini, categorizes emails into 5 buckets with reasoning
3. **Enricher** — GPT-4o-mini, extracts sender intelligence + searches Memory Core  
4. **Drafter** — GPT-4o, writes reply using few-shot retrieval from Memory Core
5. **Approver** — Formats Telegram card, sends, waits for decision, interprets edit instructions
6. **Sender** — Executes approved send via Gmail API, enforces database approval check

All agents use OpenAI Agents SDK for handoffs. Fallback to raw OpenAI function calling if SDK hits blockers.

## 3. Cognitive layer

- **Memory Core** — SQLite + sqlite-vss for semantic vector search
- **Learning Engine** — Real-time prompt evolution, 4-category edit classification
- **Reasoning Log** — Every agent decision logged with chain-of-thought

## 4. Technology stack

| Layer | Component |
|---|---|
| Runtime | Python 3.11 + FastAPI + Uvicorn |
| Database | SQLite (single file: `anika.db`) |
| Vector search | sqlite-vss extension |
| Public URL | Cloudflare Tunnel (free, permanent) |
| Gmail I/O | Gmail API (polling every 30s) |
| AI Engine | OpenAI GPT-4o (drafter) + GPT-4o-mini (classifier, enricher) |
| Agent framework | OpenAI Agents SDK |
| Messaging | Telegram Bot API |
| Dashboard | FastAPI + server-rendered HTML + Tailwind via CDN |
| Auto-start | NSSM (Windows service wrapper) |
| Auth (dashboard) | Localhost-only for pilot (add real auth on migration) |

## 5. Key decisions explained

**SQLite instead of Postgres** — Zero setup, single file, portable, sufficient for single-user Anika up to ~100,000 rows. sqlite-vss gives vector search equivalent to pgvector.

**Polling instead of Pub/Sub** — Gmail Pub/Sub requires domain verification we cannot do on laptop. 30-second polling is acceptable latency for approval workflow.

**Cloudflare Tunnel instead of ngrok** — Free permanent URL vs ngrok's free URL changing every restart.

**Telegram instead of WhatsApp** — Telegram Bot API is free and instant. WhatsApp Business via Meta takes 2-3 days for approval. Migrate to WhatsApp in Week 2.

**OpenAI Agents SDK instead of LangGraph** — OpenAI-native, cleaner for this use case, you specified OpenAI explicitly.

## 6. Database schema (SQLite, complete)

See full schema in `app/db/schema.sql` in the generated codebase. Key tables:

- `raw_emails` — every incoming email
- `classifications` — Classifier output
- `enrichments` — Enricher structured output  
- `drafts` — Drafter output (with `sent_status`)
- `approvals` — the approval gate
- `sent_log` — audit trail of every sent email
- `memory` + `memory_vss` — Memory Core (content + embeddings)
- `agent_prompts` — versioned, self-evolving prompts
- `reasoning_log` — chain-of-thought for every agent decision
- `clients` — existing Balakrishna clients (VIP flag for sensitive ones)
- `firm_knowledge` — firm profile KB (key-value)
- `rules` — do's, don'ts, sensitive keywords, FAQs
- `system_state` — kill switch, daily cap, counters

## 7. The approval gate (trigger-enforced)

```sql
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
```

Database-level guarantee. Cannot be bypassed from application code.

## 8. Safety layers

1. **Kill switch** — "PAUSE ANIKA" on Telegram halts all drafting within 5 seconds
2. **Topic blacklist** — Configurable sensitive keywords (legal notice, tax demand, complaint, dispute, rupee thresholds) bypass Anika entirely
3. **VIP filter** — Clients marked VIP get summary-only, no auto-draft
4. **Daily cap** — 30 sends/day in first month, configurable
5. **Database constraint** — No send without approval row (above)
6. **Undo window** — 10-second delay between approval and send for accidental taps

## 9. File structure

```
anika-balakrishna/
├── .env                        # Secrets (gitignored)
├── .gitignore
├── README.md
├── requirements.txt
├── anika.db                    # SQLite database (gitignored)
├── token.json                  # Gmail OAuth token (gitignored)
│
├── docs/
│   ├── 00_spec.md
│   ├── 01_architecture.md      # this file
│   ├── 02_nfr.md
│   └── 03_firm_profile.md      # Balakrishna training data
│
├── app/
│   ├── main.py                 # FastAPI entry
│   ├── config.py               # Env loader
│   ├── db.py                   # SQLite connection + migrations
│   │
│   ├── agents/
│   │   ├── orchestrator.py     # Anika (the main agent)
│   │   ├── classifier.py
│   │   ├── enricher.py
│   │   ├── drafter.py
│   │   ├── approver.py
│   │   ├── sender.py
│   │   └── learner.py
│   │
│   ├── tools/
│   │   ├── gmail_tool.py
│   │   ├── memory_tool.py
│   │   ├── telegram_tool.py
│   │   ├── knowledge_tool.py
│   │   └── client_tool.py
│   │
│   ├── cognitive/
│   │   ├── memory_core.py
│   │   ├── learning_engine.py
│   │   └── reasoning_log.py
│   │
│   ├── guardrails/
│   │   ├── kill_switch.py
│   │   ├── topic_blacklist.py
│   │   ├── vip_filter.py
│   │   └── daily_cap.py
│   │
│   ├── jobs/
│   │   ├── poll_gmail.py       # 30s polling loop
│   │   ├── backfill_memory.py  # Day 1 one-shot
│   │   └── weekly_review.py    # Sunday retrospective
│   │
│   └── dashboard/
│       ├── routes.py
│       └── templates/
│           ├── base.html
│           ├── inbox.html
│           ├── drafts.html
│           ├── train.html
│           ├── analytics.html
│           └── settings.html
│
├── scripts/
│   ├── setup.ps1
│   ├── start.ps1
│   ├── stop.ps1
│   └── install_service.ps1
│
└── tests/
    ├── test_classifier.py
    ├── test_enricher.py
    ├── test_drafter.py
    ├── test_approval_constraint.py
    └── fixtures/sample_enquiries.json
```

## 10. Startup sequence

```powershell
# One-time setup
.\scripts\setup.ps1

# Every time laptop boots
.\scripts\start.ps1

# To install as auto-start Windows service
.\scripts\install_service.ps1
```

## 11. Migration triggers (when to move off laptop)

Move to dedicated hardware when ANY of:
- Laptop downtime exceeds 2 hours in any rolling week
- Prakash sir reports system unreachable twice
- AK needs to travel and laptop cannot stay on 24/7
- Production load exceeds 20 enquiries/day sustained

## 12. What is NOT in v2 (deferred to v3)

- Multi-tenant architecture (Balakrishna only for v2)
- Dashboard user authentication (localhost-only for pilot)
- Proactive follow-up agent (Month 2)
- Weekly digest to Prakash sir (add after Week 1 data)
- Automated 7-year retention policy (add on migration)
- WhatsApp Business integration (Week 2 upgrade)
