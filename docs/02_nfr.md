# Anika — Non-Functional Requirements (NFR)

**Version:** 1.0
**Pairs with:** 00_spec.md (functional), 01_architecture.md (technical)

The functional spec says *what* Anika does. This document specifies *how well* she must do it — the qualities that separate a demo from a production system a CA firm can rely on.

---

## 1. Availability

| Requirement | Target | Measurement | Consequence of breach |
|---|---|---|---|
| System uptime | ≥99% | Railway dashboard + custom heartbeat | <99% → AK investigates within 24hrs |
| Gmail webhook response time | <5 seconds (p95) | Railway logs | >5s → scale Railway container |
| End-to-end enquiry → WhatsApp | <60 seconds (p95) | reasoning_log timestamp deltas | >60s → investigate slow agent |

**Acceptable downtime:** ~7.2 hours per month. If we exceed this, we add a secondary Railway region.

## 2. Performance

| Metric | Target | Notes |
|---|---|---|
| Classifier latency | <3 seconds | GPT-4o-mini call + DB write |
| Enricher latency | <5 seconds | Includes Memory Core similarity search |
| Drafter latency | <15 seconds | GPT-4o generation, 1500 tokens output |
| WhatsApp approval card delivery | <30 seconds from enquiry receipt | End-to-end |
| Sender Gmail API send | <3 seconds | After approval event |

**Target p95 total time (enquiry lands → WhatsApp card on Prakash sir's phone):** 45 seconds.

## 3. Security

### 3.1 Authentication & authorization
- Gmail OAuth: tokens stored encrypted at rest in Supabase (AES-256)
- OpenAI API keys: environment variables only, never in code, never in logs
- WhatsApp approval: phone number verification — a decision is only honored if it comes from Prakash sir's registered number
- Supabase access: service role key on Railway only; no direct database access from any other system

### 3.2 Data at rest
- All Supabase tables use native Postgres encryption
- `drafts.body` and `raw_emails.body` are sensitive client data — row-level security enforced
- Reasoning logs retained in full but access-restricted

### 3.3 Data in transit
- HTTPS only for all inter-service calls
- Gmail API: OAuth 2.0 over TLS 1.3
- WhatsApp: 360dialog handles TLS
- OpenAI: TLS 1.3

### 3.4 Principle of least privilege
- Gmail OAuth scopes: only 5 required (readonly, compose, send, labels, modify). No contacts, no drive, no calendar.
- Supabase service key scoped to `anika` schema only
- Railway deployment has no access to other MarketIQX infrastructure

### 3.5 Secret management
- No secret ever committed to GitHub
- `.env.example` lists all required env vars without values
- Railway environment variables set manually via dashboard
- Rotation policy: OpenAI key every 90 days, OAuth credentials on any suspected breach

## 4. Data retention & compliance

### 4.1 Retention schedule

| Data type | Retention | Deletion mechanism |
|---|---|---|
| Raw emails (prakasha's inbox) | Stored in Gmail (not copied by Anika beyond immediate processing) | Gmail's own retention |
| Drafts (approved + sent) | 7 years | Aligned with CA audit requirements under ICAI |
| Drafts (rejected) | 90 days | Automated deletion |
| Reasoning logs | 7 years | Aligned with audit requirements |
| Memory Core embeddings | Indefinite (anonymized after 2 years) | Manual review |
| WhatsApp messages | 90 days (on 360dialog) + indefinite reference on Supabase | 360dialog default |

### 4.2 Data residency
- Supabase region: AP Southeast (Singapore) — closest to India with equivalent data protection
- No client data leaves the Anika perimeter except to OpenAI (stateless API, no retention under default settings)
- If client demands India-only residency: migrate to Supabase India (ETA 2026) or self-host on MarketIQX Indian infrastructure (+₹1,500/month)

### 4.3 DPDP Act readiness
- Audit logs capture every data touch with timestamp, agent, purpose
- Data subject access: on request, full export of any sender's interaction history within 48 hours
- Right to erasure: on request, hard-delete of a sender's data across all tables
- Consent: Anika only processes emails received at a legitimate business mailbox — implied consent for business correspondence

## 5. Audit & compliance

### 5.1 What gets audited (every event)
- Who/what: agent name or user action
- When: millisecond-precision timestamp (Asia/Kolkata)
- What input: full JSON of the event input
- What decision: the agent's output
- Why: chain-of-thought reasoning text (for LLM agents)
- Model version: exact OpenAI model used
- Prompt version: which row of `agent_prompts` table was active

### 5.2 Immutability
- `reasoning_log` table: append-only. No updates, no deletes except automated retention sweeps.
- `sent_log` table: append-only. Every send is permanently recorded.
- Supabase triggers enforce this at the database level.

### 5.3 Exportability
- Full audit trail exportable to PDF/CSV within 5 minutes via Supabase admin dashboard
- If Prakash sir is ever asked "did someone AI-draft that email you sent me?", the answer is retrievable

## 6. Reliability & fault tolerance

### 6.1 Expected failure modes and responses

| Failure | Likelihood | Response | Recovery time |
|---|---|---|---|
| OpenAI API timeout | Medium (1-2% of calls) | Retry 3× with exponential backoff; on final fail, log error and queue for manual handling | <1 minute |
| OpenAI rate limit hit | Low | Backoff + queue; alert AK via WhatsApp if >10 queued | <5 minutes |
| Gmail API token expired | Monthly | Auto-refresh token; if refresh fails, WhatsApp alert to AK | <15 minutes |
| Railway deployment down | Rare | Auto-restart; if >2 failures in 10 min, alert AK | <30 minutes |
| Supabase outage | Very rare | Queue writes in Railway memory; alert AK; manual replay on recovery | Depends on Supabase SLA (~99.9%) |
| WhatsApp delivery failure | Low | Retry; if 3 failures, email Prakash sir as fallback | <2 minutes |
| Gmail Push webhook missed | Very low | 30-minute backup polling job catches any missed events | <30 minutes |

### 6.2 Disaster recovery
- **RPO (Recovery Point Objective):** 1 hour — max data loss in a disaster is the last 1 hour of events
- **RTO (Recovery Time Objective):** 4 hours — system restored within 4 hours of declared disaster
- Supabase daily automated backups
- GitHub as code of record — full rebuild possible from commit history in <2 hours

## 7. Scalability

### 7.1 Current load (Month 1)
- ~100 enquiries/month = ~3-4 per working day
- Comfortable on Railway starter tier (512 MB RAM, 1 vCPU)
- Supabase free tier: 500 MB storage, 2 GB bandwidth — sufficient for 2+ years

### 7.2 Year 2 projection
- If Anika rolls out to `contact@balakrishnaandco.com` firm-wide (+500 enquiries/month)
- Plus SLCPro and Simplified Laws (+200/month each)
- Total: ~1,000-1,200 enquiries/month
- Required: Railway Pro tier (₹1,600/month), Supabase Pro (₹2,000/month)
- OpenAI costs: ~₹8,000-12,000/month at this volume

### 7.3 Breaking points identified
- Above 5,000 enquiries/month: need dedicated vector DB (migrate from pgvector to Pinecone)
- Above 10,000 enquiries/month: need dedicated Railway instance per client
- Current architecture comfortable to 5,000/month without changes

## 8. Maintainability

### 8.1 Code quality standards
- Type hints on every function (Pydantic for data models)
- Every non-trivial function has a docstring explaining purpose, inputs, outputs, failure modes
- Every architectural decision has a "why this, not that" comment in-code
- Linting: ruff + mypy in CI
- Test coverage target: 70% for core agents (Classifier, Enricher, Drafter)

### 8.2 Documentation requirements
- `README.md` with 5-minute setup instructions
- `docs/04_runbook.md` with operational procedures (how to pause, how to reset, how to debug)
- Inline code comments for any non-obvious logic
- `CHANGELOG.md` for every deployed version

### 8.3 Handover readiness
- Any competent Python developer should be able to run Anika locally in <30 minutes using only the README
- All secrets documented in `.env.example` with explanations
- No "tribal knowledge" required — if it matters, it's written down

## 9. Monitoring & alerting

### 9.1 What triggers an immediate WhatsApp alert to AK
- System down >5 minutes
- 3+ consecutive agent failures
- Daily cap hit (30 sends reached)
- Any database-level approval bypass attempt (this should be architecturally impossible, so if it ever alerts, something is deeply wrong)
- OpenAI spending above ₹500 in a day

### 9.2 What gets logged but not alerted
- Individual agent errors (retried automatically)
- Classification misfires caught by human review
- Edit-heavy drafts (learning opportunity, not emergency)

### 9.3 Daily digest to AK (7 AM IST)
- Enquiries yesterday: X
- Classified as new_enquiry: Y
- Drafts generated: Z
- Approved: A, Edited: B, Rejected: C
- Avg response time: D seconds
- Any errors: list

### 9.4 Weekly summary to Prakash sir (Sunday 6 PM IST)
- Clean, non-technical WhatsApp message
- Total enquiries handled, hours saved (estimated), any patterns noticed
- No error reports — that's operational, not for him

## 10. Cost discipline

### 10.1 Monthly cost ceiling
- Total operating cost ≤₹3,500/month at current volume
- Alert if approaching ₹3,000

### 10.2 Cost per enquiry
- Target: ≤₹30 per approved enquiry
- Composed of: ~₹10 OpenAI, ~₹6 WhatsApp, ~₹4 Railway, ~₹0 Supabase (free tier), ~₹10 buffer

### 10.3 Cost review
- AK reviews monthly invoice from OpenAI, 360dialog, Railway
- Quarterly optimization pass: can any GPT-4o calls move to 4o-mini without quality loss?
