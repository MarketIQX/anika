# Anika — Claude Code Build Prompt

**This is the prompt to paste into Claude Code when you run it in the `anika-balakrishna` folder.**

---

## Copy everything below this line and paste into Claude Code

---

You are building Anika — a fully agentic AI email assistant for CA S.V. Prakasha at Balakrishna & Co, a Chartered Accountancy firm in Bangalore.

**Context files — read these first, in this order:**

1. `docs/00_spec.md` — Business and functional requirements
2. `docs/01_architecture.md` — Technical architecture (v2, laptop deployment with SQLite)
3. `docs/02_nfr.md` — Non-functional requirements
4. `docs/03_firm_profile.md` — Balakrishna firm knowledge base (Anika's ground truth)

**Critical constraints to respect:**

- Deployment: Windows laptop (`C:\Users\marke\anika-balakrishna`)
- Database: SQLite (single file: `anika.db`) with sqlite-vss for vector search
- Public URL: Cloudflare Tunnel (set up script, don't hardcode URL yet)
- AI: OpenAI GPT-4o (drafter) + GPT-4o-mini (classifier, enricher)
- Agent framework: OpenAI Agents SDK
- Messaging: Telegram Bot API (free, instant)
- Email: Gmail API via OAuth (credentials in `.env`, token will be created on first run)
- Python 3.11 (already set up in `.venv`)

**Hard requirements — do NOT compromise on these:**

1. **Fully agentic, not scripted.** Agents reason and make decisions via function calling. No hardcoded if-else pipelines.
2. **Database-level no-send-without-approval constraint** via SQLite trigger. Must be enforced at DB layer, not application layer.
3. **Every agent decision must be logged** to `reasoning_log` table with chain-of-thought.
4. **Every edit Prakash sir makes must be categorized** (style / fact / context / rejection) and routed to Learning Engine appropriately.
5. **Memory Core uses sqlite-vss** for real semantic search. No keyword matching fallback.
6. **Six agents as specified** in architecture — orchestrator Anika, Classifier, Enricher, Drafter, Approver, Sender. Plus Learning Engine (cognitive layer, not an agent).

**Build order:**

1. Full file structure (per architecture doc section 9)
2. Database schema + migrations (with the approval trigger)
3. Tools (gmail_tool, memory_tool, telegram_tool, knowledge_tool, client_tool)
4. Cognitive layer (memory_core, learning_engine, reasoning_log)
5. Agents (orchestrator, classifier, enricher, drafter, approver, sender, learner)
6. Guardrails (kill_switch, topic_blacklist, vip_filter, daily_cap)
7. Jobs (poll_gmail, backfill_memory, weekly_review)
8. Dashboard (FastAPI routes + HTML templates for inbox, drafts, train, analytics, settings)
9. Scripts (setup.ps1, start.ps1, stop.ps1, install_service.ps1)
10. Tests (fixtures + test cases for each agent, especially approval constraint)

**What I (AK) will handle — ask me for these when you need them:**

- Creating Telegram bot via BotFather (2 min) — give you the bot token
- OpenAI API key (already in `.env` — check first)
- Gmail OAuth consent from Prakash sir (one-time)
- Cloudflare Tunnel setup on my laptop (first-time cloudflared install)
- Populating VIP sender list in dashboard
- Loading the firm_profile.md content into firm_knowledge table on first boot

**What you should NOT ask me — just do:**

- Install Python packages (via pip in the existing venv)
- Create file structure
- Write code
- Write SQL schemas
- Write tests
- Configure logging
- Create configuration files
- Run local testing commands

**When you hit genuine blockers, ask me ONE clear question. No long explanations. Just the question.**

**Style for code:**

- Type hints everywhere (Pydantic for data models)
- Every function has a docstring (purpose, inputs, outputs, failure modes)
- Every architectural decision has a "why this, not that" comment inline
- Follow the folder structure in `docs/01_architecture.md` section 9
- Use async/await where appropriate (FastAPI native)
- Log structured JSON for every agent call (for dashboard observability)

**Goal:**

By end of this session, I should have:
- A working `anika-balakrishna` codebase on my Windows laptop
- Ability to run `.\scripts\start.ps1` and see Anika listening on localhost:8000
- A working dashboard at `http://localhost:8000` showing Inbox, Drafts, Train, Analytics, Settings tabs
- Sample enquiry processing end-to-end in test mode (without actually sending email)
- A README that tells me exactly what's needed from me to go live

Start now. Work autonomously. Ask only when genuinely blocked.
