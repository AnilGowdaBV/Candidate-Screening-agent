# Candidate Screening Agent
**Instahyre + GitHub | Go/Golang Verification**

A local-only, production-grade screening tool designed to process candidate profiles from a configured Instahyre search query, discover public GitHub profiles, verify evidence of Go/Golang code via the official GitHub REST API, and add exact status notes to candidate profiles when authorized.

---

## 🌟 Key Features

- **100% Local Execution:** Runs entirely on your local Windows PC without third-party hosting.
- **Zero Paid AI APIs:** Deterministic language detection using GitHub's official REST API (`/users/{username}/repos`, `/repos/{owner}/{repo}/languages`, byte statistics, and repo topics).
- **Exact Candidate Note Rules:**
  - **Rule A (No GitHub profile):** Adds note `No GitHub found`.
  - **Rule B (GitHub found, Go not detected):** Adds note `Go lang not found`.
  - **Rule C (Go detected):** **Zero notes added.** Candidate left unchanged; recorded as `GO_DETECTED`.
  - **Rule D (Incomplete check / rate limit / API error):** **Zero notes added.** Routed to manual review.
- **Triple-Layer Duplicate Prevention:**
  1. Pre-write check against local SQLite database.
  2. Pre-write check of existing notes on the candidate's Instahyre profile DOM.
  3. Post-write confirmation check before marking success.
- **Persistent Browser Context:** Preserves login session cookies in `backend/data/browser_profile`.
- **State Machine Control:** Supports safe **Start**, **Pause**, **Resume**, and **Stop** with candidate-by-candidate checkpointing.
- **Real-Time Developer Dashboard:** Modern dark-themed UI (Vite + React + TypeScript) with Server-Sent Events (SSE) live activity feed, metrics, current operation card, and candidate explorer.

---

## 🏗️ Architecture

```
CANDIDATE SCREENING AGENT/
├── README.md                      # Complete system documentation
├── .env.example                   # Configuration template with placeholders
├── .env                           # Local environment configuration (kept private)
├── .gitignore                     # Git ignore rules for virtualenv, DB, profile, etc.
├── start_agent.bat                # Windows one-click launcher for backend & frontend
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point & CORS configuration
│   │   ├── api/routes/            # health.py, candidates.py, runs.py, events.py
│   │   ├── core/                  # config.py, logging.py, state.py
│   │   ├── models/                # SQLAlchemy 2.x models (Candidate, Run, Result, Note, Event)
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── services/              # screening_service.py, github_service.py, notes_service.py, event_service.py
│   │   ├── browser/               # browser_manager.py, selectors.py
│   │   ├── repositories/          # candidate_repo.py, screening_repo.py
│   │   └── database/              # session.py, migrations/ (Alembic)
│   ├── tests/                     # 37 automated Pytest unit & integration tests
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/            # Header, ControlPanel, CurrentOperationCard, MetricsCards, etc.
    │   ├── services/              # api.ts (REST client & SSE streaming)
    │   ├── types/                 # TypeScript interfaces matching backend models
    │   ├── App.tsx                # Dashboard root application
    │   └── index.css              # Dark developer tool design system
    ├── package.json
    └── vite.config.ts
```

---

## 🚀 Windows Setup & Quick Start

### 1. Prerequisites
- **Python:** 3.12+ installed and on PATH.
- **Node.js:** v18+ with `npm`.

### 2. Configure Environment (`.env`)
Copy `.env.example` to `.env` (already done locally) and configure your keys:
```env
# Operational Controls
DRY_RUN=true                    # Keep true initially to simulate without writing notes
HEADLESS_BROWSER=false          # Set to false to see the browser window

# GitHub REST API Token (Optional but recommended for 5,000 req/hr rate limits)
GITHUB_TOKEN=your_github_personal_access_token_here

# Instahyre Credentials (Automated Login)
INSTAHYRE_EMAIL=your_email@example.com
INSTAHYRE_PASSWORD=your_password_here
```
> **Security Note:** The backend strictly isolates `GITHUB_TOKEN` and `INSTAHYRE_PASSWORD`. They are never returned by API routes, never exposed to React, and never printed in logs.

---

### 3. Launching the Application
You can start both backend and frontend using the provided Windows script:
```bash
start_agent.bat
```

Or manually in two separate terminal windows:

#### Terminal 1 — Backend (FastAPI on Port 8000)
```powershell
backend\venv\Scripts\activate
$env:PYTHONPATH="backend"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Terminal 2 — Frontend (Vite on Port 5173)
```powershell
cd frontend
npm.cmd run dev
```

Open your browser to: **`http://localhost:5173`**

---

## ⚙️ Operating the Screening Agent

1. **Dashboard Header:** Verifies that SQLite, GitHub API, and Instahyre configurations are operational.
2. **Execution Controls:**
   - **Start:** Validates prerequisites, checks database readiness, and initializes candidate screening.
   - **Pause:** Halts processing safely at the current candidate boundary and persists a checkpoint.
   - **Resume:** Picks up from the last confirmed checkpoint without repeating completed work.
   - **Stop:** Halts new operations, preserves all SQLite database records, and closes the browser context.
3. **What is the Agent Doing Right Now? Card:** Displays human-readable live operations, active candidate name, last completed step, and planned next step.
4. **Candidate Explorer:** Search by candidate name, profile URL, or GitHub username. Filter by Go classification or Note status.

---

## 🧪 Running Automated Tests

Run the full backend test suite (37 tests):
```powershell
backend\venv\Scripts\python.exe -m pytest -v
```

Run frontend type check & production build:
```powershell
cd frontend
npm.cmd run build
```

---

## 🛡️ Troubleshooting & Recovery

- **GitHub Rate Limit Exceeded:** Add a free GitHub Personal Access Token (`GITHUB_TOKEN`) to `.env` to increase your rate limit from 60 to 5,000 requests per hour.
- **Instahyre Bot Challenge / CAPTCHA:** If Instahyre displays an unexpected CAPTCHA, the agent pauses automatically. Log in manually in the visible browser window, then press **Resume** in the dashboard.
- **Recovering After Interruption:** All candidate records, screening results, notes, and checkpoints are stored immediately in `backend/data/screening_agent.db`. If stopped or restarted, simply click **Start** to resume without writing duplicate notes.
