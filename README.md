# JobPilot - Job Application AI Agent

A semi-autonomous AI agent that manages your job applications end-to-end -- searching jobs across major portals, tailoring resumes, filling application forms, tracking everything in Google Sheets, syncing Gmail for responses, and handling follow-ups. Interact through Telegram, WhatsApp, or a full Web UI.

Built with [OpenClaw](https://docs.openclaw.ai) + Python MCP servers + free cloud LLM APIs.

## Features

- **Job Search** -- Scrapes LinkedIn, Indeed, Naukri, Glassdoor, Wellfound
- **Resume Tailoring** -- Auto-tailors resume and cover letter per job (conservative, never fabricates)
- **Auto-Apply** -- Fills forms on Workday, Greenhouse, Lever, LinkedIn, Naukri, Indeed, iCIMS + generic fallback
- **Application Tracking** -- Logs everything to Google Sheets with status tracking
- **Gmail Sync** -- Monitors inbox for responses (interviews, rejections, assessments)
- **Follow-ups** -- Drafts and sends follow-up emails on configurable schedules
- **Approval Flow** -- Screenshots every form before submission, waits for your approval
- **Web Dashboard** -- Full management UI with stats, charts, chat, and settings

## Architecture

```
You (Telegram / WhatsApp / Web UI)
        |
   OpenClaw Agent (orchestrator, memory, cron)
        |
   Cloud LLM APIs (Gemini Flash -> Groq fallback)
        |
   MCP Servers (Python):
   ├── tracker            -- Google Sheets application tracking (6 tools)
   ├── job_search         -- Scrape 5 job portals + dedup (3 tools)
   ├── resume_tailor      -- PDF parsing, LLM tailoring, PDF generation (4 tools)
   ├── application_filler -- ATS detection + 8 handlers + screenshots (4 tools)
   ├── gmail_sync         -- OAuth2, inbox scanning, email classification (3 tools)
   └── followup           -- Email drafting, scheduling, sending (4 tools)
        |
   Web UI (React + FastAPI)
```

## Prerequisites

| Tool    | Version | Check              | Install                                                        |
| ------- | ------- | ------------------ | -------------------------------------------------------------- |
| Node.js | 22+     | `node --version`   | [nodejs.org](https://nodejs.org)                               |
| Python  | 3.12+   | `python --version` | [python.org](https://python.org)                               |
| Git     | any     | `git --version`    | [git-scm.com](https://git-scm.com)                            |

---

## Quick Start (New System)

### 1. Clone and install

```bash
git clone <your-repo-url> agentic_bot
cd agentic_bot
```

### 2. Install OpenClaw

```bash
npm i -g openclaw@beta
openclaw doctor
```

### 3. Create Python venv and install dependencies

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

### 4. Get API keys

| Provider         | URL                            | What to do                         |
| ---------------- | ------------------------------ | ---------------------------------- |
| Google AI Studio | [ai.google.dev](https://ai.google.dev) | Get API Key                 |
| Groq             | [console.groq.com](https://console.groq.com) | Create API Key          |

### 5. Configure OpenClaw

Create `~/.openclaw/openclaw.json`:

```json
{
  "gateway": { "mode": "local" },
  "agents": {
    "defaults": {
      "model": {
        "primary": "google/gemini-2.5-flash",
        "fallbacks": ["groq/llama-3.3-70b-versatile"]
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "groq": {
        "baseUrl": "https://api.groq.com/openai/v1",
        "apiKey": "${GROQ_API_KEY}",
        "api": "openai-completions",
        "models": [{ "id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B (Groq)", "reasoning": false }]
      }
    }
  },
  "channels": {
    "telegram": {
      "botToken": "${TELEGRAM_BOT_TOKEN}",
      "dmPolicy": "allowlist",
      "allowFrom": ["YOUR_TELEGRAM_USER_ID"]
    },
    "whatsapp": {
      "dmPolicy": "allowlist",
      "allowFrom": ["+91XXXXXXXXXX"]
    }
  },
  "mcp": {
    "servers": {
      "tracker": {
        "transport": "stdio",
        "command": ".venv/Scripts/python",
        "args": ["-m", "mcp-servers.tracker.server"],
        "env": { "GOOGLE_SERVICE_ACCOUNT_FILE": "${GOOGLE_SERVICE_ACCOUNT_FILE}" }
      },
      "job_search": {
        "transport": "stdio",
        "command": ".venv/Scripts/python",
        "args": ["-m", "mcp-servers.job_search.server"]
      },
      "resume_tailor": {
        "transport": "stdio",
        "command": ".venv/Scripts/python",
        "args": ["-m", "mcp-servers.resume_tailor.server"]
      },
      "application_filler": {
        "transport": "stdio",
        "command": ".venv/Scripts/python",
        "args": ["-m", "mcp-servers.application_filler.server"]
      },
      "gmail_sync": {
        "transport": "stdio",
        "command": ".venv/Scripts/python",
        "args": ["-m", "mcp-servers.gmail_sync.server"]
      },
      "followup": {
        "transport": "stdio",
        "command": ".venv/Scripts/python",
        "args": ["-m", "mcp-servers.followup.server"]
      }
    }
  },
  "env": {
    "GOOGLE_API_KEY": "<your-key>",
    "GROQ_API_KEY": "<your-key>",
    "TELEGRAM_BOT_TOKEN": "<your-token>",
    "GOOGLE_SERVICE_ACCOUNT_FILE": "data/service-account.json"
  },
  "plugins": { "entries": { "google": { "enabled": true } } }
}
```

> **Linux/macOS**: Change MCP `command` paths from `.venv/Scripts/python` to `.venv/bin/python`

### 6. Google Sheets Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project, enable **Sheets API** + **Drive API**
3. Create Service Account > download JSON key > save as `data/service-account.json`
4. Create a Google Sheet named **Job Application Tracker**
5. Share it with the service account email (Editor access)
6. Test: `python mcp-servers/tracker/test_tracker.py`

### 7. Gmail Setup (for sync + follow-ups)

1. Google Cloud Console > APIs & Services > Credentials
2. Create **OAuth 2.0 Client ID** (Desktop App)
3. Download JSON > save as `data/gmail_credentials.json`
4. First run will open browser for OAuth consent
5. Token auto-saves to `data/gmail_token.json`

### 8. Telegram Bot

1. Message `@BotFather` > `/newbot`
2. Get your user ID from `@userinfobot`
3. Update `openclaw.json` with token + user ID

### 9. WhatsApp

```bash
openclaw channels login --channel whatsapp
```
Scan QR code with WhatsApp.

### 10. Start the Gateway

```bash
openclaw gateway
```

### 11. Web UI (optional)

**Backend:**
```bash
cd web/backend
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd web/frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Project Structure

```
agentic_bot/
├── .gitignore
├── .env.example                       # Environment variable template
├── README.md
├── requirements.txt                   # All Python dependencies
├── docker-compose.yml                 # Docker deployment
├── Dockerfile.mcp                     # MCP servers container
├── Dockerfile.web                     # Web UI container
├── openclaw/                          # Agent personality & rules
│   ├── AGENTS.md                      # Behavior rules
│   ├── SOUL.md                        # Personality
│   ├── USER.md                        # Your profile
│   └── IDENTITY.md                    # Agent name: JobPilot
├── mcp-servers/
│   ├── tracker/                       # Google Sheets tracker (6 tools)
│   │   ├── server.py
│   │   └── test_tracker.py
│   ├── job_search/                    # Job portal scrapers (3 tools)
│   │   ├── server.py
│   │   ├── models.py
│   │   ├── dedup.py
│   │   └── scrapers/                  # LinkedIn, Indeed, Naukri, Glassdoor, Wellfound
│   ├── resume_tailor/                 # Resume tailoring (4 tools)
│   │   ├── server.py
│   │   ├── parser.py
│   │   ├── tailor.py
│   │   ├── generator.py
│   │   └── templates/                 # HTML templates for PDF generation
│   ├── application_filler/            # Form filling (4 tools)
│   │   ├── server.py
│   │   ├── detector.py
│   │   ├── screenshot.py
│   │   └── handlers/                  # 8 ATS handlers
│   ├── gmail_sync/                    # Gmail integration (3 tools)
│   │   ├── server.py
│   │   ├── auth.py
│   │   ├── reader.py
│   │   └── matcher.py
│   └── followup/                      # Follow-up emails (4 tools)
│       ├── server.py
│       ├── drafter.py
│       ├── sender.py
│       └── scheduler.py
├── web/
│   ├── backend/                       # FastAPI backend
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   └── routes/                    # API routes
│   └── frontend/                      # React + Vite + TailwindCSS
│       ├── package.json
│       ├── vite.config.ts
│       └── src/
│           ├── pages/                 # Dashboard, Applications, Search, Chat, Settings
│           ├── components/
│           └── lib/api.ts
├── data/
│   ├── base_resume.pdf                # Your master resume
│   ├── base_resume.json               # Parsed structured resume
│   ├── profile.json                   # Personal details
│   ├── preferences.json               # Job search preferences
│   ├── service-account.json           # Google Sheets key (GITIGNORED)
│   ├── gmail_credentials.json         # Gmail OAuth client (GITIGNORED)
│   └── gmail_token.json               # Gmail auth token (GITIGNORED)
├── generated/
│   ├── resumes/                       # Tailored resume PDFs
│   ├── cover_letters/                 # Cover letter PDFs
│   └── screenshots/                   # Application form screenshots
└── deploy/
    ├── oracle-setup.sh                # Oracle Cloud VM setup script
    └── nginx.conf                     # Reverse proxy config
```

## MCP Server Tools Summary

| Server               | Tools | Description |
| -------------------- | ----- | ----------- |
| **tracker**          | 6     | initialize_sheet, log_application, update_status, get_all_applications, get_pending_followups, get_stats |
| **job_search**       | 3     | search_jobs, search_all_platforms, get_job_details |
| **resume_tailor**    | 4     | parse_resume_pdf, tailor_resume_for_job, generate_cover_letter_for_job, list_generated_documents |
| **application_filler** | 4   | detect_ats, fill_application, submit_application, get_application_screenshot |
| **gmail_sync**       | 4     | check_gmail_auth, check_new_responses, classify_email_by_id, sync_all |
| **followup**         | 4     | check_due_followups, draft_followup, send_followup, draft_thank_you |

**Total: 25 tools across 6 MCP servers**

## Supported ATS Platforms

LinkedIn Easy Apply, Workday, Greenhouse, Lever, Naukri, Indeed, iCIMS, + generic fallback (LLM-guided form filling for unknown ATS)

## Cloud Deployment (Docker)

```bash
cp .env.example .env
# Edit .env with your keys

docker compose up -d

# For WhatsApp 24/7 via Evolution API:
docker compose --profile whatsapp up -d
```

## Troubleshooting

| Issue | Fix |
| ----- | --- |
| Spreadsheet not found | Name must be exactly "Job Application Tracker", shared with service account email |
| Service account not found | Place at `data/service-account.json` |
| Telegram not connecting | Check internet (corporate networks block Telegram) |
| LLM not responding | Run `openclaw gateway status`, check API keys |
| Playwright errors | Run `playwright install chromium` |
| Gmail auth fails | Delete `data/gmail_token.json` and re-authenticate |
| Gateway port in use | `openclaw gateway stop` or kill node processes |

## Build Progress

- [x] Phase 1 -- Foundation (OpenClaw, LLM, Telegram, WhatsApp, Tracker)
- [x] Phase 2 -- Job Search (LinkedIn, Indeed, Naukri, Glassdoor, Wellfound scrapers)
- [x] Phase 3 -- Resume & Cover Letter (PDF parsing, LLM tailoring, PDF generation)
- [x] Phase 4 -- Auto-Apply (8 ATS handlers, screenshots, approval flow)
- [x] Phase 5 -- Gmail Sync & Follow-ups (OAuth2, classification, drafting, sending)
- [x] Phase 6 -- Web UI (React dashboard, FastAPI backend, chat, settings)
- [x] Phase 7 -- Cloud Deployment (Docker, Oracle Cloud, Nginx, Evolution API)

## License

Private project -- not for distribution.
