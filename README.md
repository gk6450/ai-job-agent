# JobPilot — AI Job Application Agent

A semi-autonomous AI agent that manages job applications end-to-end. It searches jobs across 5 major portals, scores them against your resume, auto-applies to high-match roles, tracks everything in Google Sheets, monitors Gmail for responses, auto-updates your tracker, and handles follow-up emails — all through Telegram, WhatsApp, or a web dashboard.

Built with [OpenClaw](https://docs.openclaw.ai) as the orchestration framework, Python [MCP](https://modelcontextprotocol.io/) servers for tooling, and free-tier cloud LLM APIs (Gemini + Groq).

---

## Features

| Category | What it does |
|----------|-------------|
| **Job Search** | Scrapes LinkedIn, Indeed, Naukri, Glassdoor, Wellfound. Deduplicates cross-platform results. |
| **Match Scoring** | Scores every listing 0–100% against your resume and preferences. |
| **Auto-Apply** | Jobs scoring ≥ 85% are applied to automatically with your base resume. Below that, it asks. |
| **Daily Scan** | Automated daily search using your target roles and preferred locations. |
| **Resume Handling** | Prefers your original resume. Only tailors when clearly needed — never fabricates. |
| **Cover Letters** | LLM-generated, under 300 words, specific to the job description. |
| **Form Filling** | Handles Workday, Greenhouse, Lever, LinkedIn, Naukri, Indeed, iCIMS + generic fallback. |
| **Screenshots** | Captures every form page before submission for your review. |
| **Application Tracking** | Logs every application to Google Sheets with status, dates, notes. |
| **Gmail Sync** | Monitors inbox, classifies responses (interview/rejection/offer/assessment). |
| **Auto-Tracker Update** | Automatically updates the tracker sheet when Gmail finds a response — no approval needed. |
| **Follow-ups** | Configurable: remind only, draft for review, or auto-send first follow-ups. |
| **Web Dashboard** | React UI with stats, charts, application table, chat interface, and settings. |
| **Notifications** | Every auto-action (apply, tracker update) is reported via WhatsApp/Telegram/Web. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     YOUR CHANNELS                        │
│     Telegram  ←→  WhatsApp  ←→  Web UI (React)          │
└────────────────────────┬────────────────────────────────┘
                         │
                ┌────────▼────────┐
                │  OpenClaw Agent │   AGENTS.md (rules)
                │  (orchestrator) │   SOUL.md (personality)
                │  memory + cron  │   USER.md (your profile)
                └────────┬────────┘
                         │  calls 28 tools via MCP protocol
          ┌──────────────┼───────────────────────┐
          │              │                       │
     ┌────▼────┐   ┌─────▼──────┐   ┌───────────▼───────────┐
     │ tracker │   │ job_search │   │   resume_tailor       │
     │ (6 tools)│   │ (6 tools)  │   │ (5 tools)             │
     │ Sheets  │   │ 5 scrapers │   │ parse/tailor/PDF      │
     └─────────┘   │ + scorer   │   └───────────────────────┘
                   └────────────┘
     ┌─────────────┐  ┌───────────┐  ┌─────────────────────┐
     │ gmail_sync  │  │ followup  │  │ application_filler  │
     │ (4 tools)   │  │ (4 tools) │  │ (4 tools)           │
     │ auto-update │  │ draft/send│  │ 8 ATS handlers      │
     └─────────────┘  └───────────┘  └─────────────────────┘
          │                │                    │
     Gmail API        Gmail API           Playwright
     (read inbox)     (send emails)       (fill forms)
                                               │
                                          ┌────▼────┐
                                          │ Web UI  │
                                          │ FastAPI │
                                          │ React   │
                                          └─────────┘
```

### How a typical flow works

1. **Daily scan** runs automatically → searches all 5 portals for your target roles
2. **Scorer** rates each listing against your resume (title 30pts, skills 35pts, location 15pts, remote 10pts, experience 10pts)
3. Jobs **≥ 85%** → auto-filled with base resume, screenshot taken, applied, logged to tracker
4. Jobs **< 85%** → presented to you with match scores, you pick which ones to apply to
5. **Gmail sync** monitors inbox → classifies responses → **auto-updates tracker** (Interview Scheduled, Rejected, etc.)
6. **Follow-up scheduler** checks for due follow-ups → drafts/sends based on your policy
7. Everything is **notified** to you via WhatsApp/Telegram/Web

---

## LLM Configuration

The agent uses free-tier cloud LLM APIs with automatic failover:

| Provider | Model | Role | Free Tier Limits | Tool Calling |
|----------|-------|------|-----------------|--------------|
| **Google AI Studio** | Gemini 2.5 Flash | Primary | 10 RPM, 500 RPD, 250K TPM | Yes |
| **Groq** | Llama 4 Scout 17B | Fallback | 30 RPM, 1K RPD, 30K TPM | Yes |

**Daily capacity**: ~500 Gemini requests/day is enough for ~50 searches + ~20 tailoring calls + ~30 misc operations. If Gemini hits its 10 RPM limit, the agent auto-falls back to Groq.

---

## Prerequisites

| Tool | Version | Check | Install |
|------|---------|-------|---------|
| Node.js | 22+ | `node --version` | [nodejs.org](https://nodejs.org) |
| Python | 3.12+ | `python --version` | [python.org](https://python.org) |
| Git | any | `git --version` | [git-scm.com](https://git-scm.com) |
| Docker | latest | `docker --version` | [docker.com](https://docker.com) *(only for Docker deployment)* |

---

## Setup (Local Development)

### Step 1: Clone

```bash
git clone https://github.com/gk6450/ai-job-agent.git
cd ai-job-agent
```

### Step 2: Install OpenClaw

```bash
npm i -g openclaw@beta
openclaw doctor
```

### Step 3: Python environment

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Step 4: Get API keys

| Service | URL | What to get |
|---------|-----|-------------|
| Google AI Studio | [ai.google.dev](https://ai.google.dev) | API Key (Gemini 2.5 Flash) |
| Groq | [console.groq.com](https://console.groq.com) | API Key (Llama 4 Scout fallback) |
| Telegram BotFather | [t.me/BotFather](https://t.me/BotFather) | Bot token via `/newbot` |

### Step 5: Configure OpenClaw (auto-generated)

OpenClaw's gateway needs **absolute paths** to the venv Python interpreter and to each MCP `server.py` (it does not yet support a `cwd` field for stdio servers). Rather than hand-editing those paths every time you move to a new machine, copy `.env.example` to `.env`, fill in your secrets, and run the generator:

```bash
cp .env.example .env       # Linux/macOS
copy .env.example .env     # Windows PowerShell
```

Edit `.env` and set at minimum:

- `GOOGLE_API_KEY` (required)
- `GROQ_API_KEY` (recommended — fallback model)
- `TELEGRAM_BOT_TOKEN` and `ALLOWED_TELEGRAM_ID` (if using Telegram)
- `ALLOWED_WHATSAPP_NUMBER` (if using WhatsApp, in E.164 form e.g. `+91XXXXXXXXXX`)
- `OPENCLAW_GATEWAY_TOKEN` (optional — pin the gateway auth token; otherwise a random one is generated each run)

Then generate the OpenClaw config:

```bash
python tools/setup_openclaw_config.py            # writes ~/.openclaw/openclaw.json
python tools/setup_openclaw_config.py --dry-run  # preview without writing
```

The script:
1. Reads `config/openclaw.template.json`
2. Loads values from `.env` (falls back to OS env vars)
3. Auto-detects the venv Python (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere)
4. Substitutes absolute paths for this machine
5. Backs up any existing `openclaw.json` to `openclaw.json.bak`
6. Writes the result to `~/.openclaw/openclaw.json`

Re-run it any time you move the repo, switch machines, or rotate secrets.

### Step 6: Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **Google Sheets API** + **Google Drive API**
3. Create a **Service Account** → download the JSON key
4. Save it as `data/service-account.json`
5. Create a Google Sheet named exactly **Job Application Tracker**
6. Share the sheet with the service account email (Editor access)
7. Test:

```bash
python mcp-servers/tracker/test_tracker.py
```

### Step 7: Your resume

Copy your resume PDF into the project:

```bash
cp /path/to/your/resume.pdf data/base_resume.pdf
```

### Step 8: Fill in preferences

Edit `data/preferences.json` — replace all `FILL_IN` values:

```json
{
  "preferred_locations": ["Bangalore", "Chennai", "Remote"],
  "open_to_remote": true,
  "preferred_company_size": "any",
  "salary_minimum_lpa": 8,
  "salary_expected_lpa": 12
}
```

Also check `data/profile.json` for any remaining `FILL_IN` placeholders.

### Step 9: Start the gateway

```bash
cd ai-job-agent
openclaw gateway start
openclaw gateway status
openclaw status
```

Expected output:

- `openclaw gateway status` → `Runtime: running` and `Connectivity probe: ok`
- `openclaw status` → `Telegram: ON · OK`, `Agents: 1`, sessions present
- `openclaw agents list` → `Identity: JobPilot (IDENTITY.md)` and `Workspace: <repo>/openclaw`

> **Cosmetic warning to ignore:** `openclaw status` may show `Bootstrap file: ABSENT` for the `main` agent. This is OpenClaw's flag for a per-agent provenance file it generates internally — it does **not** mean your AGENTS.md / SOUL.md / USER.md / IDENTITY.md aren't loading. As long as `openclaw agents list` shows `Identity: JobPilot (IDENTITY.md)`, the workspace is wired correctly.

#### Open the OpenClaw Dashboard (web chat + logs + sessions)

```
http://127.0.0.1:18789/
```

Bookmark this — it's your primary "control panel" for the agent. From here you can:

- Chat with JobPilot in a browser (no Telegram needed for testing)
- View live logs and MCP tool-call traces
- Browse session history and switch sessions
- See channel status (Telegram / WhatsApp)

If a server is unhealthy, view logs:

```bash
openclaw logs --follow
```

Most failures are path mismatches — re-run `python tools/setup_openclaw_config.py`, then `openclaw gateway restart`.

### Step 10: Smoke-test all MCP servers

Optional but recommended — catches dep/import issues before talking to the agent:

```powershell
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'mcp-servers/tracker'); import server; print('tracker OK')"
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'mcp-servers/job_search'); import server; print('job_search OK')"
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'mcp-servers/resume_tailor'); import server; print('resume_tailor OK')"
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'mcp-servers/application_filler'); import server; print('application_filler OK')"
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'mcp-servers/gmail_sync'); import server; print('gmail_sync OK')"
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'mcp-servers/followup'); import server; print('followup OK')"
```

All six should print `… OK`.

### Step 11: Connect Telegram

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token → put it in `.env` as `TELEGRAM_BOT_TOKEN`
2. DM [@userinfobot](https://t.me/userinfobot) → copy your numeric `Id:` → put it in `.env` as `ALLOWED_TELEGRAM_ID`
3. Re-generate the OpenClaw config so it picks up the values:
   ```bash
   python tools/setup_openclaw_config.py
   openclaw gateway stop
   openclaw gateway start
   ```
4. From your phone, DM your bot — try `List my applications` to confirm the round-trip works

### Step 12: Connect WhatsApp

```bash
openclaw channels login --channel whatsapp
```

Scan the QR code with WhatsApp.

### Step 13: Gmail setup (for sync + follow-ups)

Gmail uses **OAuth user consent** (different from the service account used for Sheets). The Sheets account and Gmail account can be **different Google accounts** — the GCP project just needs to allow the Gmail account as a test user.

#### 13.1 Configure the OAuth consent screen

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **same project** you used for Sheets
2. **APIs & Services → OAuth consent screen** → click **Get started**
3. Walk through the wizard:
   - **App name**: `JobPilot` (any)
   - **User support email**: dropdown → your account
   - **Audience**: **External**
   - **Contact information**: same email
   - Tick the user-data-policy checkbox → **Continue → Create**
4. Once on the OAuth dashboard → left menu → **Audience** → scroll to **Test users** → **+ Add users** → enter the Gmail account whose inbox you want the agent to monitor → **Save**

   > Test users can be different from your GCP account. As long as they're listed here, OAuth will succeed for them in Testing mode (up to 100 users — no need to publish the app).

#### 13.2 Create the OAuth client

1. Left menu → **Clients** → **+ Create client**
2. **Application type: Desktop app**
3. Name: `JobPilot Desktop`
4. **Create** → in the popup, **Download JSON**
5. Save as `data/gmail_credentials.json` in the repo root
6. Verify the file structure:

   ```bash
   .venv/Scripts/python.exe -c "import json; print(list(json.load(open('data/gmail_credentials.json')).keys()))"
   ```

   Must print `['installed']`. If it prints `['web']` you created the wrong client type — delete it and recreate as **Desktop app**.

#### 13.3 Enable the Gmail API

In the same project: [console.developers.google.com](https://console.developers.google.com) → search **Gmail API** → click **Enable**. Wait ~30 seconds for it to propagate.

#### 13.4 Run the OAuth consent flow (one-time browser pop)

```bash
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'mcp-servers/gmail_sync'); from auth import get_gmail_service; s = get_gmail_service(); print('Gmail OK:', s.users().getProfile(userId='me').execute().get('emailAddress'))"
```

A browser opens:
1. Pick the **Gmail account whose inbox you want monitored** (the one you added as a test user)
2. You'll see "Google hasn't verified this app" → **Advanced → Go to JobPilot (unsafe)** (safe — you're the developer)
3. Grant the requested Gmail permissions → **Continue**
4. Browser shows "authentication flow has completed"

Terminal should print `Gmail OK: yourgmail@gmail.com`. The token is cached at `data/gmail_token.json` — future runs won't open the browser.

#### Common errors

| Error | Fix |
|---|---|
| `Client secrets must be for a web or installed app` | The downloaded JSON isn't a Desktop client. Verify with the diagnostic in 13.2 and re-download. |
| `403 Gmail API has not been used in project ... or it is disabled` | Step 13.3 missed — enable Gmail API and wait 30-60s |
| `Access blocked: This app's request is invalid` | Test user not added in step 13.1 — add the email under Audience → Test users |

To re-bind to a different Gmail account: delete `data/gmail_token.json` and re-run the auth command.

### Step 14: PDF generation (WeasyPrint + GTK runtime)

Required for tailored resume PDFs and cover letter PDFs.

**Linux/macOS:** WeasyPrint's system deps come with the OS or are easily `apt`/`brew` installable — see [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

**Windows:** install GTK3 runtime:

1. Download the latest installer from [GTK-for-Windows-Runtime-Environment-Installer releases](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) (look for `gtk3-runtime-X.X.X-X-X-X-ts-win64.exe`)
2. Run with default options — it adds itself to PATH
3. **Close PowerShell completely and reopen it** so the new PATH is picked up
4. Verify:

   ```powershell
   .venv\Scripts\activate
   .venv\Scripts\python.exe -c "from weasyprint import HTML; HTML(string='<h1>hello</h1>').write_pdf('test.pdf'); print('PDF OK')"
   del test.pdf
   ```

   Expected: prints `PDF OK` and creates `test.pdf` in the repo root.

If you get `cannot load library 'libgobject-2.0-0'`, the installer didn't update PATH. Manually add `C:\Program Files\GTK3-Runtime Win64\bin` to your **User PATH** via Windows Settings → System → About → Advanced system settings → Environment Variables, then close and reopen PowerShell.

> WeasyPrint is imported lazily inside `mcp-servers/resume_tailor/generator.py`, so the MCP server starts fine even without GTK — but PDF generation calls will fail with a clear error until you install it.

### Step 15: Web UI (JobPilot Mission Control)

The OpenClaw dashboard (Step 9) handles chat + logs. The custom Web UI adds the things OpenClaw can't show:

- **Dashboard** — application stats, charts (apply-rate, response-rate over time), recent activity feed
- **Applications** — pipeline (Pending Review → Applied → Interview → Offer / Rejected) with kanban-style filters, status updates
- **Job Search** — fire ad-hoc searches with form-based filters (keywords, location, platforms, remote, experience)
- **Resume Review** — preview tailored resumes / cover letters side-by-side with the original; approve / reject
- **Chat** — alternative chat surface (proxies to OpenClaw gateway)
- **Settings** — edit `data/profile.json` and `data/preferences.json`, view connection health (Sheets, Gmail, Telegram)

**Stack:** FastAPI backend + React 19 + Vite + TailwindCSS + Recharts + Lucide icons

#### 15.1 Install Node 22+ if not already

```powershell
node --version
```

If missing or < 22, install from [nodejs.org/en/download](https://nodejs.org/en/download) (LTS).

#### 15.2 Install frontend dependencies (one-time)

```powershell
cd web\frontend
npm install
cd ..\..
```

This pulls React 19, Vite 6, Tailwind 4, axios, recharts, and lucide-react (~150 MB into `web/frontend/node_modules`). Takes 1–2 minutes.

#### 15.3 Run the backend (Terminal 1)

```powershell
cd ai-job-agent
.venv\Scripts\activate
python -m uvicorn web.backend.main:app --reload --port 8000
```

Expected: `Application startup complete.` and `Uvicorn running on http://127.0.0.1:8000`. 

Health check (in a 3rd terminal):
```powershell
curl http://127.0.0.1:8000/api/health
```
Should return `{"status":"ok","service":"jobpilot-web"}`.

#### 15.4 Run the frontend dev server (Terminal 2)

```powershell
cd ai-job-agent\web\frontend
npm run dev
```

Expected:
```
VITE v6.x ready in 412 ms
➜  Local:   http://localhost:5173/
```

Open [http://localhost:5173](http://localhost:5173) → JobPilot Mission Control.

The frontend's `vite.config.ts` proxies `/api/*` to `http://localhost:8000`, so both servers must be running.

#### 15.5 Common Web UI issues

| Symptom | Fix |
|---|---|
| `npm install` fails with `EACCES` / permission errors on Windows | Run PowerShell as Administrator once for the install |
| Backend errors on startup: `ModuleNotFoundError: No module named 'web'` | Run uvicorn from the **repo root**, not from `web/backend` |
| Frontend loads but every page shows "Network Error" | Backend isn't running on port 8000 — check Terminal 1 |
| Backend `Forbidden` on every API call | Set `JOBPILOT_WEB_TOKEN=jobpilot-local-dev` in your env (or whatever you set in `web/backend/config.py`) |
| `getApplications()` returns 500 | Sheets credentials missing — re-check Step 6 (`data/service-account.json` and tracker test) |
| Tailwind classes not applying | Vite proxy or PostCSS issue — run `npm run dev` once more after a fresh `npm install` |

#### 15.6 Production build (optional)

```powershell
cd web\frontend
npm run build
```

This creates `web/frontend/dist/` — when present, the FastAPI backend (Step 15.3) auto-serves it from `/`, so you only need **one process** in production. Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

---

### Auto-generated files (don't worry about these)

OpenClaw and the test scripts create some files at runtime. Here's what's safe to delete vs. leave alone:

| File | Created by | Safe to delete? |
|---|---|---|
| `~\.openclaw\agents\main\agent\HEARTBEAT.md` | OpenClaw runtime (per restart) | No — auto-recreated; deleting won't break anything but it'll come back |
| `~\.openclaw\agents\main\agent\TOOLS.md` | OpenClaw runtime | No — same as above |
| `~\.openclaw\agents\main\agent\models.json` | OpenClaw runtime | No |
| `~\.openclaw\agents\main\sessions\sessions.json` | OpenClaw chat sessions | Deletes your chat history — usually leave |
| `test.pdf` (repo root) | Step 14 verification command | **Yes** — `del test.pdf` |
| `data/gmail_token.json` | Step 13.4 OAuth flow | Only delete to re-auth a different Gmail account |
| `generated/*.pdf`, `generated/*.html` | Resume tailor MCP outputs | **Yes** — these are throwaway artifacts per application |

If you accidentally copied `AGENTS.md` / `SOUL.md` / `USER.md` / `IDENTITY.md` into `~\.openclaw\agents\main\agent\` while debugging, you can safely delete them — OpenClaw reads those from your repo's `openclaw/` workspace, not from the per-agent dir:

```powershell
Remove-Item ~\.openclaw\agents\main\agent\AGENTS.md, ~\.openclaw\agents\main\agent\SOUL.md, ~\.openclaw\agents\main\agent\USER.md, ~\.openclaw\agents\main\agent\IDENTITY.md -ErrorAction SilentlyContinue
```

---

## Setup (Docker Deployment)

For 24/7 operation on a cloud server (e.g., Oracle Cloud Always Free).

### Step 1: Prepare the server

```bash
# On a fresh Ubuntu VM
bash deploy/oracle-setup.sh
```

### Step 2: Clone and configure

```bash
git clone https://github.com/gk6450/ai-job-agent.git
cd ai-job-agent
cp .env.example .env
```

Edit `.env` with your API keys:

```env
GOOGLE_API_KEY=your-google-ai-studio-key
GROQ_API_KEY=your-groq-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
GOOGLE_SERVICE_ACCOUNT_FILE=data/service-account.json
JOBPILOT_WEB_TOKEN=a-random-secret-string
```

### Step 3: Place credentials

```bash
# Copy your files into data/
cp /path/to/service-account.json data/service-account.json
cp /path/to/base_resume.pdf data/base_resume.pdf
```

### Step 4: Start all services

```bash
docker compose up -d
```

This starts 3 containers:
- **openclaw** — Agent gateway on port 18789
- **mcp-servers** — All Python MCP servers
- **web** — FastAPI backend + React frontend on port 8000

### Step 5: WhatsApp 24/7 (optional)

To run WhatsApp via Evolution API instead of local Baileys:

```bash
docker compose --profile whatsapp up -d
```

This adds Evolution API on port 8080 for persistent WhatsApp connections.

### Step 6: Setup Nginx + SSL

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/jobpilot
sudo ln -s /etc/nginx/sites-available/jobpilot /etc/nginx/sites-enabled/
# Edit server_name in the config to your domain
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

### Docker commands reference

```bash
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose logs -f web        # View web UI logs
docker compose logs -f openclaw   # View agent logs
docker compose restart mcp-servers # Restart MCP servers
docker compose --profile whatsapp up -d  # Include WhatsApp
```

---

## Testing Sequence

After setup, verify each component in this order:

| # | Test | Command |
|---|------|---------|
| 1 | Gateway health | `openclaw gateway status` |
| 2 | Initialize tracker | `openclaw agent --agent main --message "Initialize the tracker sheet"` |
| 3 | Job search | `openclaw agent --agent main --message "Search for React developer jobs in Bangalore"` |
| 4 | Daily scan | `openclaw agent --agent main --message "Run a daily scan"` |
| 5 | Job details | `openclaw agent --agent main --message "Get details for <url>"` |
| 6 | Gmail auth | `openclaw agent --agent main --message "Check Gmail auth status"` |
| 7 | Stats | `openclaw agent --agent main --message "Show my application stats"` |
| 8 | Follow-ups | `openclaw agent --agent main --message "Check for due follow-ups"` |

---

## Autonomy Levels

| Action | Approval needed? |
|--------|-----------------|
| Search jobs | No — runs autonomously |
| Daily scheduled scan | No — automatic |
| Score and rank results | No — automatic |
| Auto-apply (≥ 85% match) | No — applies with base resume, notifies you after |
| Apply (< 85% match) | **Yes** — asks for approval |
| Tailor resume | No — but shows you before using it |
| Fill application form | No — but screenshots for review before submit |
| Submit application | **Yes** — waits for your "submit" |
| Update tracker on Gmail response | No — auto-updates, notifies you |
| Send follow-up email | Depends on policy setting (remind / draft / auto-send) |
| Send thank-you email | **Yes** — always drafted for review |

---

## Configuration Reference

### `data/preferences.json`

```json
{
  "target_roles": ["Software Engineer", "Full Stack Developer"],
  "preferred_locations": ["Bangalore", "Chennai", "Remote"],
  "open_to_remote": true,
  "salary_minimum_lpa": 8,
  "auto_apply_enabled": true,
  "auto_apply_threshold": 85,
  "auto_apply_use_base_resume": true,
  "auto_tracker_update_on_gmail": true,
  "daily_scan_enabled": true,
  "daily_scan_time": "09:00",
  "max_applications_per_day": 10,
  "followup_policy_default": "draft_for_review",
  "followup_days_first": 7,
  "followup_days_second": 14
}
```

### `data/profile.json`

Personal details used for form filling: name, email, phone, location, LinkedIn URL, GitHub URL, education, experience, current company/title.

---

## MCP Server Tools

| Server | Tools | Description |
|--------|-------|-------------|
| **tracker** | 6 | `initialize_sheet`, `log_application`, `update_status`, `get_all_applications`, `get_pending_followups`, `get_stats` |
| **job_search** | 6 | `search_jobs`, `search_all_platforms`, `get_job_details`, `daily_scan`, `get_auto_apply_candidates`, `score_job` (internal) |
| **resume_tailor** | 5 | `parse_resume_pdf`, `get_base_resume_path`, `tailor_resume_for_job`, `generate_cover_letter_for_job`, `list_generated_documents` |
| **application_filler** | 4 | `detect_ats`, `fill_application`, `submit_application`, `get_application_screenshot` |
| **gmail_sync** | 4 | `check_gmail_auth`, `check_new_responses`, `classify_email_by_id`, `sync_all` |
| **followup** | 4 | `check_due_followups`, `draft_followup`, `send_followup`, `draft_thank_you` |

**Total: 29 tools across 6 MCP servers**

### Supported ATS Platforms

LinkedIn Easy Apply, Workday, Greenhouse, Lever, Naukri, Indeed, iCIMS, + generic fallback for unknown ATS types.

---

## Project Structure

```
ai-job-agent/
├── README.md
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment variable template
├── .gitignore
├── docker-compose.yml                  # Docker deployment (3 services + optional WhatsApp)
├── Dockerfile.mcp                      # MCP servers container
├── Dockerfile.web                      # Web UI container
│
├── openclaw/                           # Agent configuration
│   ├── AGENTS.md                       # Behavior rules & autonomy levels
│   ├── SOUL.md                         # Personality & tone
│   ├── USER.md                         # Your profile & experience
│   └── IDENTITY.md                     # Agent name: JobPilot
│
├── mcp-servers/
│   ├── tracker/                        # Google Sheets tracker
│   │   ├── server.py                   # 6 tools: log, update, query, stats
│   │   └── test_tracker.py             # Standalone test script
│   │
│   ├── job_search/                     # Multi-platform job search
│   │   ├── server.py                   # 6 tools: search, scan, score, details
│   │   ├── models.py                   # JobListing, SearchQuery, SearchResult
│   │   ├── scorer.py                   # 0-100 match scoring engine
│   │   ├── dedup.py                    # Fuzzy deduplication
│   │   └── scrapers/                   # Platform-specific scrapers
│   │       ├── base.py                 # Abstract scraper with retry logic
│   │       ├── linkedin.py             # Playwright-based
│   │       ├── indeed.py               # httpx + BeautifulSoup
│   │       ├── naukri.py               # httpx + BeautifulSoup
│   │       ├── glassdoor.py            # Playwright-based
│   │       └── wellfound.py            # httpx + BeautifulSoup
│   │
│   ├── resume_tailor/                  # Resume & cover letter generation
│   │   ├── server.py                   # 5 tools: parse, get, tailor, cover, list
│   │   ├── parser.py                   # PDF → structured JSON
│   │   ├── tailor.py                   # LLM-based conservative tailoring
│   │   ├── generator.py               # HTML → PDF via WeasyPrint
│   │   └── templates/                  # Jinja2 HTML templates
│   │       ├── resume.html
│   │       └── cover_letter.html
│   │
│   ├── application_filler/             # Automated form filling
│   │   ├── server.py                   # 4 tools: detect, fill, submit, screenshot
│   │   ├── detector.py                 # ATS type detection (URL + DOM)
│   │   ├── screenshot.py               # Full-page & element capture
│   │   └── handlers/                   # ATS-specific form handlers
│   │       ├── base.py                 # Abstract handler with safe_fill/click/select
│   │       ├── linkedin_easy_apply.py
│   │       ├── workday.py
│   │       ├── greenhouse.py
│   │       ├── lever.py
│   │       ├── naukri_apply.py
│   │       ├── indeed_apply.py
│   │       ├── icims.py
│   │       └── generic_fallback.py     # Pattern-based for unknown ATS
│   │
│   ├── gmail_sync/                     # Gmail monitoring
│   │   ├── server.py                   # 4 tools: auth, check, classify, sync
│   │   ├── auth.py                     # OAuth2 flow + token management
│   │   ├── reader.py                   # Email fetching & parsing
│   │   └── matcher.py                  # Email → application matching + classification
│   │
│   └── followup/                       # Follow-up email management
│       ├── server.py                   # 4 tools: check, draft, send, thank-you
│       ├── drafter.py                  # LLM-based email drafting
│       ├── sender.py                   # Gmail API send
│       └── scheduler.py               # Due date calculation
│
├── web/
│   ├── backend/                        # FastAPI backend
│   │   ├── main.py                     # App entry, CORS, route registration
│   │   ├── auth.py                     # Bearer token auth
│   │   ├── config.py                   # Paths, URLs, CORS origins
│   │   └── routes/
│   │       ├── applications.py         # CRUD for tracked applications
│   │       ├── search.py              # Job search API
│   │       ├── resume.py              # Resume download & tailor
│   │       ├── gmail.py               # Gmail sync endpoints
│   │       ├── settings.py            # Profile & preferences CRUD
│   │       └── chat.py                # WebSocket chat with agent
│   │
│   └── frontend/                       # React + Vite + TailwindCSS
│       ├── package.json
│       ├── vite.config.ts
│       └── src/
│           ├── main.tsx                # Router setup
│           ├── index.css               # Dark theme styles
│           ├── lib/api.ts              # Typed API client
│           ├── components/Layout.tsx   # Sidebar + header
│           └── pages/
│               ├── Dashboard.tsx       # Stats, charts, activity
│               ├── Applications.tsx    # Filterable table + detail modal
│               ├── JobSearch.tsx       # Search form + results
│               ├── ResumeReview.tsx    # Generated docs + tailor form
│               ├── Chat.tsx           # WebSocket chat with agent
│               └── Settings.tsx       # Profile, preferences, connections
│
├── data/                               # User data (mostly gitignored)
│   ├── base_resume.pdf                 # Your master resume (GITIGNORED)
│   ├── base_resume.json                # Parsed structured version
│   ├── profile.json                    # Personal details for form filling
│   ├── preferences.json                # Search & automation settings
│   ├── service-account.json            # Google Sheets key (GITIGNORED)
│   ├── gmail_credentials.json          # Gmail OAuth client (GITIGNORED)
│   └── gmail_token.json                # Gmail auth token (GITIGNORED)
│
├── generated/                          # Output files (gitignored contents)
│   ├── resumes/                        # Tailored resume PDFs
│   ├── cover_letters/                  # Cover letter PDFs
│   └── screenshots/                    # Application form screenshots
│
└── deploy/                             # Cloud deployment configs
    ├── oracle-setup.sh                 # Oracle Cloud VM setup script
    └── nginx.conf                      # Reverse proxy + WebSocket config
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `openclaw: command not found` | `npm i -g openclaw@beta` |
| Gateway port 18789 in use | `openclaw gateway stop` or kill node processes |
| `Bootstrap file: ABSENT` for `main` agent | Cosmetic — verify with `openclaw agents list`, should show `Identity: JobPilot (IDENTITY.md)`. Workspace is loaded; this label is for an internal OpenClaw provenance file. |
| `gateway connect failed: scope upgrade pending approval` | Cosmetic — gateway still works. It's the Telegram native-approvals handler asking for permissions. Ignore unless you want phone-button approvals. |
| `openclaw devices approve <id>` says `unknown requestId` | Each restart issues a new requestId; the old one is stale. Either re-read logs for the latest, or ignore (gateway runs fine without it). |
| Spreadsheet not found | Sheet name must be exactly "Job Application Tracker", shared with service account email |
| `service-account.json` not found | Place at `data/service-account.json` and set path in `openclaw.json` |
| Telegram not connecting | Corporate networks often block Telegram — try personal network |
| LLM not responding | `openclaw gateway status`, verify API keys in `openclaw.json` |
| Gemini 429 rate limit | Normal — agent auto-falls back to Groq. Wait 60s for Gemini to reset. |
| Playwright errors | Run `playwright install chromium` (needs venv activated) |
| Gmail auth fails | Delete `data/gmail_token.json` and re-authenticate |
| Web UI can't connect | Ensure backend is running on port 8000, check CORS_ORIGINS |
| Web UI: `ModuleNotFoundError: No module named 'web'` | Run `uvicorn` from repo root, not from `web/backend/` |
| Web UI: `npm install` fails on Windows | Run PowerShell as Administrator once |
| Web UI: 403 Forbidden on every API call | Set `JOBPILOT_WEB_TOKEN=jobpilot-local-dev` in env, or check `web/backend/auth.py` |
| `[postcss] tailwindcss directly as a PostCSS plugin` on `npm run dev` | Tailwind v4 uses `@tailwindcss/vite` (already in `vite.config.ts`) — delete `web/frontend/postcss.config.js` if it exists, then `npm install && npm run dev` |
| Docker build fails | Add swap: `sudo fallocate -l 4G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |

---

## License

Private project — not for distribution.
