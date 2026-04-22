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
openclaw gateway
```

Keep this terminal running.

### Step 10: Test the agent

In a new terminal:

```bash
openclaw agent --agent main --message "Hello, what can you do?"
```

### Step 11: Connect Telegram

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token
2. Get your user ID from [@userinfobot](https://t.me/userinfobot)
3. Update `openclaw.json` with the token and user ID
4. Restart the gateway
5. Message your bot on Telegram

### Step 12: Connect WhatsApp

```bash
openclaw channels login --channel whatsapp
```

Scan the QR code with WhatsApp.

### Step 13: Gmail setup (for sync + follow-ups)

1. Google Cloud Console → enable **Gmail API**
2. Credentials → Create **OAuth 2.0 Client ID** (Desktop App)
3. Download JSON → save as `data/gmail_credentials.json`
4. The first sync will open a browser window for OAuth consent
5. Test:

```bash
openclaw agent --agent main --message "Check Gmail auth status"
```

### Step 14: Web UI (optional)

**Terminal 1** — Backend:
```bash
cd ai-job-agent
python -m uvicorn web.backend.main:app --reload --port 8000
```

**Terminal 2** — Frontend:
```bash
cd ai-job-agent/web/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

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
| Spreadsheet not found | Sheet name must be exactly "Job Application Tracker", shared with service account email |
| `service-account.json` not found | Place at `data/service-account.json` and set path in `openclaw.json` |
| Telegram not connecting | Corporate networks often block Telegram — try personal network |
| LLM not responding | `openclaw gateway status`, verify API keys in `openclaw.json` |
| Gemini 429 rate limit | Normal — agent auto-falls back to Groq. Wait 60s for Gemini to reset. |
| Playwright errors | Run `playwright install chromium` (needs venv activated) |
| Gmail auth fails | Delete `data/gmail_token.json` and re-authenticate |
| Web UI can't connect | Ensure backend is running on port 8000, check CORS_ORIGINS |
| Docker build fails | Add swap: `sudo fallocate -l 4G /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |

---

## License

Private project — not for distribution.
