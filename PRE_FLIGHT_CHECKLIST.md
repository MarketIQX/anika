# Anika — Pre-flight checklist before running Claude Code

**Read this BEFORE you run Claude Code. 10 minutes of prep = smooth autonomous build.**

---

## 1. Verify folder structure on your laptop

```powershell
cd C:\Users\marke\anika-balakrishna
```

Check these exist:
- `.env` (with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
- `.gitignore`
- `.venv\` folder (Python virtual environment)

If any missing, re-run last night's PowerShell steps.

---

## 2. Download the 4 docs to your laptop

From this chat's outputs, download:
- `00_spec.md`
- `01_architecture.md` 
- `02_nfr.md`
- `03_firm_profile.md`

Put them in:
```
C:\Users\marke\anika-balakrishna\docs\
```

Create the `docs` folder if it doesn't exist:
```powershell
New-Item -ItemType Directory -Path "docs" -Force
```

---

## 3. Get your OpenAI API key into .env

Add to `.env`:
```
OPENAI_API_KEY=sk-proj-your-actual-openai-key-here
```

Your MarketIQX OpenAI key (the one you use for Priya/Arjun). If unsure:
- Go to `platform.openai.com/api-keys`
- Create a new key named "Anika"
- Paste into .env

---

## 4. Create Telegram bot (2 minutes)

1. On your phone, open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Name: `Anika for Prakash sir`
5. Username: `anika_balakrishna_bot` (must end in `bot`)
6. BotFather gives you a token like `123456:ABCdef...`
7. Add to `.env`:

```
TELEGRAM_BOT_TOKEN=123456:ABCdef-your-actual-token
```

8. Send any message to your new bot to activate chat
9. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
10. Find your chat ID in the response
11. Add to `.env`:

```
AK_TELEGRAM_CHAT_ID=your-chat-id
```

(Prakash sir's chat ID comes later, when he first messages the bot.)

---

## 5. Install Cloudflare Tunnel (cloudflared)

One-time. Takes 5 minutes.

```powershell
# Download cloudflared for Windows
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"

# Move to project folder
Move-Item cloudflared.exe C:\Users\marke\anika-balakrishna\cloudflared.exe
```

Login to Cloudflare (free account if you don't have one):
```powershell
.\cloudflared.exe tunnel login
```

Browser opens → login to Cloudflare → authorize.

Create a tunnel:
```powershell
.\cloudflared.exe tunnel create anika
```

Copy the tunnel ID that prints out. Claude Code will configure the rest.

---

## 6. Install Claude Code (if not already installed)

```powershell
npm install -g @anthropic-ai/claude-code
```

Or if using direct install method Anthropic provides — follow their docs.

Verify:
```powershell
claude --version
```

---

## 7. Final check — what .env should contain

```
GOOGLE_CLIENT_ID=27206901551-xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
PRAKASHA_EMAIL=prakasha@balakrishnaandco.com
OPENAI_API_KEY=sk-proj-xxxxx
TELEGRAM_BOT_TOKEN=123456:ABCdef-xxxxx
AK_TELEGRAM_CHAT_ID=xxxxx
PRAKASHA_TELEGRAM_CHAT_ID=   # Leave empty for now
CLOUDFLARE_TUNNEL_NAME=anika
```

---

## 8. Run Claude Code

```powershell
cd C:\Users\marke\anika-balakrishna
claude
```

When Claude Code opens, paste the content of `CLAUDE_CODE_PROMPT.md`.

Claude Code will start reading docs and building autonomously. Expect 2-4 hours of autonomous work.

---

## 9. What to do during the build

**Mostly nothing.** Claude Code will:
- Install Python packages
- Write code
- Run tests locally
- Configure databases
- Create the dashboard

**Check in every 30 minutes.** Answer questions if Claude Code asks. Most questions will be single-word (yes/no or pick A/B).

---

## 10. Expected deliverables at end of build

- Complete `anika-balakrishna` codebase
- Working `anika.db` SQLite database with all tables
- Dashboard accessible at `http://localhost:8000`
- All tests passing
- README with "what to do next" instructions

---

## 11. After the build

Two things remaining, both with Prakash sir (max 30 minutes total):

1. **Gmail OAuth consent** — 5 minutes
2. **First live test enquiry** — 10 minutes

After that, Anika is live on your laptop.

---

## 12. If something goes wrong

Common issues:

**"OpenAI API key invalid"** — check .env, regenerate if needed
**"Cloudflare tunnel not found"** — re-run `cloudflared tunnel create anika`
**"Telegram bot not responding"** — check token, message the bot once to activate
**"sqlite-vss not installing"** — Windows has issues sometimes; fallback to simple cosine similarity in Python

If stuck, copy Claude Code's last error message and paste it here. I debug with you.

---

## Ready?

Complete steps 1-7 above, then open Claude Code and paste the prompt.

**Go.**
