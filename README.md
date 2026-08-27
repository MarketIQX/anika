# Anika — AI email assistant for CA 

Anika is a fully agentic AI email assistant that reads every new enquiry at
`email`, drafts a reply in Prakash sir's voice, and
presents it on a web dashboard for **one-click approval**. Nothing sends
without Prakash sir's explicit tap.

- **Six agents** via OpenAI Agents SDK: Orchestrator, Classifier, Enricher,
  Drafter, Approver, Sender + Learner (cognitive layer).
- **Database-enforced approval gate** — no draft can be marked `sent`
  without a matching approvals row. Trigger is a DB-level `RAISE(ABORT)`.
- **Semantic memory** via SQLite + [`sqlite-vec`][vec] (the Windows-friendly
  successor to sqlite-vss).
- **Self-evolving prompts** — every edit Prakash sir makes is classified
  (style / fact / context / rejection) and routed through the Learning
  Engine to evolve the Drafter prompt in real time.
- **Approval notifications by email**, not Telegram/WhatsApp. Prakash sir
  gets a 1-line email per pending draft with a link to the dashboard.

## Architecture at a glance

```
Gmail inbox
    │  (30-sec poll)
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Orchestrator│ ──► │  Classifier  │ ──► │   Enricher   │ ──► │    Drafter   │
│   (Python)   │     │ (gpt-4o-mini)│     │ (gpt-4o-mini)│     │   (gpt-4o)   │
└──────┬───────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
       │                                                              │
       │          Sensitive bypass · VIP filter · Kill switch         │
       │                                                              ▼
       │                                                       ┌──────────────┐
       │                                                       │ email notify │
       │                                                       │  to Prakash  │
       │                                                       │    sir       │
       │                                                       └──────┬───────┘
       │                                                              │
       ▼                                                       Dashboard approval
┌──────────────┐                                                      │
│ raw_emails   │                                                      ▼
│ classifications                                              ┌──────────────┐
│ enrichments  │                                               │   Approver   │
│ drafts       │                                               │  (Python)    │
│ approvals    │◄──────────────────────────────────────────────┴──────┬───────┘
│ sent_log     │                                                      │
│ memory + vec │                                                      ▼
│ reasoning_log│                                               ┌──────────────┐
│ agent_prompts│   Learner (edit classification + prompt       │   Sender     │
│ ...          │   evolution) writes new versions here ───────►│ (Gmail send) │
└──────────────┘                                               └──────────────┘
```

## What's in the box

| Path | What |
|---|---|
| `app/main.py` | FastAPI entry + startup wiring |
| `app/config.py` | Pydantic settings (reads `.env`) |
| `app/db/schema.sql` | SQLite schema with `enforce_approval_before_send` trigger |
| `app/agents/` | Six agents + schemas + Agents SDK tool adapters |
| `app/cognitive/` | Memory Core, Learning Engine, Reasoning Log |
| `app/tools/` | Gmail, memory, knowledge, client, notify |
| `app/guardrails/` | kill switch, topic blacklist, VIP filter, daily cap |
| `app/jobs/` | Gmail poller, day-1 backfill, weekly review |
| `app/dashboard/` | FastAPI routes + Jinja2 templates (Tailwind CDN) |
| `app/auth/` | Login, session cookies, bcrypt, RBAC, audit log |
| `scripts/` | `setup.ps1`, `start.ps1`, `stop.ps1`, `install_service.ps1`, `set_password.ps1`, `create_user.ps1` |
| `app/tools/web_form_parser.py` | Extracts the real enquirer from website-form notifications |
| `tests/` | 82 tests — approval-constraint, 23 auth, 19 account-password, 17 web-form |

## First-time setup (on this laptop)

Already done if you're reading this on `C:\Users\marke\anika-balakrishna`:
- Python 3.11 venv at `.venv/`
- `requirements.txt` packages installed
- `.env` with OpenAI + Google keys
- SQLite database seeded with firm_knowledge, rules, and initial prompts

Re-run from scratch:
```powershell
.\scripts\setup.ps1
```

## Running Anika

```powershell
# Foreground, localhost only
.\scripts\start.ps1

# Foreground + Cloudflare Tunnel (see "Going live" below)
.\scripts\start.ps1 -Tunnel

# Install as a Windows service (auto-start on boot)
.\scripts\install_service.ps1
```

Once running, open **http://localhost:8000** — you land on the login screen.
After signing in, you land on the Drafts tab.

Tabs (visibility depends on role — see [Authentication](#authentication)):
- **Drafts** — the approval queue; this is the daily surface for Prakash sir.
- **Inbox** — every email Anika has seen, with classification + draft history.
- **Train** — agent prompt versions and recent learning events.
- **Analytics** — last-7-day counts, agent latency, error log.
- **Settings** — kill switch, Gmail OAuth, VIP list, rules, firm knowledge.

## Authentication

Anika's dashboard requires login. Two users are created on first boot:

| User | Email | Role | Can see |
|---|---|---|---|
| AK (MarketIQX) | `email` | `admin` | Drafts · Inbox · **Train** · **Analytics** · Settings (full) · Audit log |
| Prakash sir | `balakrishnaandco.com` | `user` | Drafts · Inbox · Settings (kill switch + Gmail status only) |

The `user` role **cannot**: open Train/Analytics/Audit, run Gmail OAuth,
seed memory vectors, add/remove clients, view rules or firm knowledge.
Both roles can halt Anika via the kill switch — that's a safety control.

### Initial passwords (first boot only)

Set these in `.env` **before the first start**:

```
AK_INITIAL_PASSWORD=<a-long-password>
PRAKASHA_INITIAL_PASSWORD=<another-long-password>
```

If either is left blank, Anika generates a random password and prints
it **once** to the console during startup, inside a loud banner like:

```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! INITIAL PASSWORDS (save these now, they will not be shown again)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  admin : 
  user  : 
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Change them at once via scripts\set_password.ps1 or the login form.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

After this first boot, the env vars are ignored. User rows persist in
the `users` table.

### Rotating a password

**Self-service (any logged-in user):** click **Change password** in the
header → enter current + new + confirm. Policy: ≥ 10 characters, must
contain at least one letter and one digit, must differ from the current
password. Session stays active on success.

**Admin recovery (CLI):** if a user forgets their password, AK can reset
it from the project root:

```powershell
.\scripts\set_password.ps1 -Email aks@marketiqx.com
# prompts for new password (not echoed)
```

### Adding a new user

```powershell
.\scripts\create_user.ps1 -Email new.person@example.com -Role user
# prompts for password
```

### Sessions

- Cookies are signed with `SESSION_SECRET` using `itsdangerous`; tampering
  invalidates them.
- 7-day max age (configurable via `SESSION_MAX_AGE_DAYS`).
- Set `SESSION_COOKIE_SECURE=true` in `.env` once Anika is behind HTTPS
  (Cloudflare Tunnel counts). This also flips on `Strict-Transport-Security`.
- Rotate `SESSION_SECRET` and restart to invalidate every live session.

### Audit log

Every login (success & failure), logout, draft approval / edit / reject,
kill-switch toggle, client add/remove/VIP-toggle, Gmail OAuth flow, and
poll-now button click is recorded in the append-only `access_log` table.

AK can view it at **Settings → Open audit log**. `access_log` has
DB-level triggers blocking UPDATE and DELETE.

### Security headers

The app sets `X-Content-Type-Options`, `X-Frame-Options: DENY`,
`Referrer-Policy`, and a minimal `Content-Security-Policy` on every
response. `Strict-Transport-Security` is added automatically when
`SESSION_COOKIE_SECURE=true`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The **most important test** is `tests/test_approval_constraint.py` — it
proves that a forged `UPDATE drafts SET sent_status='sent'` without an
approved row is aborted by the database.

`tests/test_auth.py` covers 23 cases: password hashing, login success/failure,
logout, unauthenticated redirects, role-based protection of Train /
Analytics / audit log / client management, session-tamper rejection,
bootstrap seed behaviour (both env-var and random-generation paths), and
the append-only invariant on `access_log`.

## What you (AK) still need to do to go live

All of these are one-time and take < 30 minutes total.

### 0. Set initial passwords and session secret (2 min)

Before the first start, edit `.env`:

```
AK_INITIAL_PASSWORD=<pick-a-long-one>
PRAKASHA_INITIAL_PASSWORD=<pick-another>
SESSION_SECRET=<64+ random chars>
```

If you leave the password vars blank, Anika generates them and prints
once to console — fine for a dev boot, not fine for production.

### 1. Grant Gmail OAuth consent from Prakash sir's browser (5 min)

Anika needs permission to read + send mail on `prakasha@balakrishnaandco.com`.

**Option A — on Prakash sir's laptop**
1. With Anika running on his laptop, open `http://localhost:8000/settings`.
2. Click **Run OAuth flow** under "Gmail connection".
3. The browser will prompt him to grant the 5 requested scopes (readonly,
   compose, send, labels, modify). He signs in with his Google account for
   `prakasha@balakrishnaandco.com`.
4. `token.json` is written to the project root. That's it.

**Option B — one-time CLI on your laptop, then copy token**
1. Put `prakasha@balakrishnaandco.com` on the Google Cloud project's OAuth
   consent screen as an authorised test user.
2. Run `python -m app.tools.gmail_tool auth` from the project root.
3. A browser opens — sign in as Prakash sir, approve scopes.
4. `token.json` is created. Ship this file to the production laptop.

### 2. Seed the memory vectors (1 min)

From Settings → "Seed memory vectors" button. This calls OpenAI embeddings
once for each of the ~10 seed firm-positioning snippets and service-line
exemplars. Costs ≈ ₹0.05. After this, the Drafter has real few-shot context.

### 3. Populate the VIP client list (5 min)

Settings → "VIP clients" table. Add the 10–20 clients Prakash sir wants to
always handle personally. VIP senders bypass the Drafter; a 1-line email
still alerts him.

### 4. Set the public URL for notification emails (5 min)

If running from `http://localhost:8000` only, the link in notification
emails will be a localhost URL — fine as long as Prakash sir checks email
on the same laptop.

To make it accessible from his phone:

```powershell
# One-time Cloudflare Tunnel install (from PRE_FLIGHT_CHECKLIST.md)
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"
.\cloudflared.exe tunnel login
.\cloudflared.exe tunnel create anika
```

Then in `.env`, set `ANIKA_PUBLIC_BASE_URL=https://<your-tunnel-hostname>`,
restart Anika, and start with `-Tunnel`:

```powershell
.\scripts\stop.ps1
.\scripts\start.ps1 -Tunnel
```

### 5. Flip off test mode for real sends (1 line)

In `.env`, set `ANIKA_TEST_MODE=false` (it already is). In test mode,
Sender writes `sent_log` rows but does not call the Gmail API — useful for
verifying the pipeline without real emails going out.

### 6. First live test (10 min)

1. Ask a colleague to send an obvious test enquiry to
  email m` ("Hi, I'm an NRI looking for ITR help…").
2. Within 30 seconds, the poller picks it up → classifier → enricher →
   drafter → Prakash sir gets an email like *"Anika: draft ready for
   approval (HOT [nri_tax])"* with a dashboard link.
3. He opens the dashboard, reads the draft, clicks **✓ Approve & Send**.
4. After the 10-second undo window, the reply fires via Gmail and lands in
   his Sent folder.

If anything misbehaves, the kill switch on the Settings page halts all
drafting and sending immediately.

## How Anika picks up enquiries

**Gmail query (targeted):**

```
from:emailsubject:"Balakrishna and Co"
  is:unread -label:Anika/Processed newer_than:7d
```

This picks up only the website-form notification emails (which the mailer
sends FROM Prakash sir's own address with that exact subject). It never
scans the rest of his inbox.

**Read state is sacred.** Anika does **not** remove the `UNREAD` label. Once
it has processed a message, it applies a custom `Anika/Processed` label
(auto-created on first use, shown as a nested "Anika ▸ Processed" label
in Gmail). The Gmail query excludes this label, so messages are picked up
at most once. Prakash sir can still see the original notifications in his
inbox as unread — Anika never silently empties the inbox under him.

**Web-form substitution.** The website mailer sends FROM Prakash sir's own
address — if Anika replied to the From header it would mail him back at
himself. Instead, the orchestrator parses the mailer HTML (via
`app/tools/web_form_parser.py`), extracts the real enquirer's name, email,
phone, and message, and substitutes them before the classifier sees the
email. The substituted fields are what persist in `raw_emails`; an
`is_web_form=1` flag tells the Sender to start a fresh outbound thread
(no `In-Reply-To` / `References` back into Prakash sir's mailbox).

## Safety guarantees (defence in depth)

1. **Kill switch** — Settings toggle, ≤ 1s to take effect.
2. **Topic blacklist** — configurable substrings (e.g. "legal notice", "tax
   demand") bypass Anika entirely.
3. **Rupee threshold** — any enquiry mentioning Rs > 50 lakhs bypasses.
4. **VIP filter** — flagged clients get summary-only, no auto-draft.
5. **Daily cap** — 30 sends/day (configurable). Hard refusal beyond.
6. **Undo window** — 10 seconds between approval and actual send.
7. **Database trigger** — `enforce_approval_before_send` aborts any
   attempt to mark a draft `sent` without an `approved` row. Tested.
8. **Append-only logs** — `sent_log`, `reasoning_log`, and `access_log`
   reject UPDATE and DELETE at the DB level.
9. **Dashboard auth** — bcrypt passwords, signed session cookies, role
   split (admin vs user), every state-changing action audited. See
   [Authentication](#authentication).

## What's NOT in v1 (deliberate)

- Multi-tenant support (Balakrishna only).
- Dashboard user authentication (localhost-only pilot; add real auth
  when migrating off laptop).
- WhatsApp / Telegram notifications (email-only per engagement decision).
- Proactive follow-up agent.
- Automated 7-year retention sweeps (manual for now).

## Operating runbook

- **Logs:** `data/logs/anika.out.log` and `data/logs/anika.err.log` (when
  installed as a Windows service via NSSM).
- **Pause Anika:** Settings → Kill switch → "Halt".
- **Force a poll:** Settings → "Poll now".
- **Reset daily counter:** happens automatically at UTC midnight.
- **Rotate OpenAI key:** update `.env`, restart.
- **Upgrade packages:** `pip install -U -r requirements.txt` in the venv.

[vec]: https://github.com/asg017/sqlite-vec
