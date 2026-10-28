# 🚀 Commands Reference Guide — Candidate Screening Agent

This document lists all commands to run, test, and manage the Candidate Screening Agent on Windows.

---

## 📦 First-Time Setup on a New Machine

### Option A: One-Click Automated Setup (Windows)
Double-click:
```cmd
setup_new_machine.bat
```
This automatically:
1. Verifies Python 3.10+ and Node.js 18+
2. Creates the Python virtual environment (`backend\venv`)
3. Installs all Python backend dependencies (`requirements.txt`)
4. Installs Playwright Chromium browser binaries
5. Installs Frontend dependencies (`npm install`)
6. Creates `.env` from template if not present

### Option B: Manual Setup (Terminal)
```powershell
# 1. Setup Backend
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
python -m playwright install chromium

# 2. Setup Frontend
cd frontend
npm install
cd ..

# 3. Setup Configuration
copy .env.example .env
```

---

## ⚡ Starting the Agent

### Option 1: One-Click Startup (Easiest)
Double-click:
```cmd
start_agent.bat
```
This automatically starts:
1. **Backend:** FastAPI server on `http://127.0.0.1:8000`
2. **Frontend:** Vite React Dashboard on `http://127.0.0.1:5173`

---

## 💻 Option 2: Running via Terminal / Command Prompt

### 1. Start Backend Server (FastAPI)
Run from the root project directory:
```powershell
# Set Python path to backend directory
$env:PYTHONPATH="backend"

# Start Uvicorn server
backend\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Backend API URL:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`

---

### 2. Start Frontend Dashboard (React + Vite)
Open a new terminal and run:
```powershell
cd frontend
npm.cmd run dev
```
- **Dashboard UI URL:** `http://localhost:5173`

---

## 🧪 Testing Commands

### Run Full Backend Test Suite (37 Tests)
```powershell
backend\venv\Scripts\python.exe -m pytest -v
```

### Run Tests for Specific Modules
```powershell
# Test Note Rules A, B, C, D and Duplicate Guardrails
backend\venv\Scripts\python.exe -m pytest -v backend/tests/test_notes_guardrails.py

# Test Official GitHub REST API & Go Detection
backend\venv\Scripts\python.exe -m pytest -v backend/tests/test_github_service.py

# Test Playwright Browser Selectors & Note Actions
backend\venv\Scripts\python.exe -m pytest -v backend/tests/test_browser_manager.py

# Test SQLite Models, Deduplication & Database Constraints
backend\venv\Scripts\python.exe -m pytest -v backend/tests/test_database.py
```

### Verify Frontend TypeScript Build Check
```powershell
cd frontend
npm.cmd run build
```

### One-Click Test Runner
Double-click:
```cmd
run_tests.bat
```

---

## 🛠️ Database & Maintenance Commands

### Apply Database Migrations (Alembic)
```powershell
backend\venv\Scripts\alembic.exe upgrade head
```

### Generate New Database Migration
```powershell
backend\venv\Scripts\alembic.exe revision --autogenerate -m "migration_description"
```

### Reset Database
To start with a clean database, delete `backend/data/screening_agent.db` and run:
```powershell
backend\venv\Scripts\alembic.exe upgrade head
```
*(Or let the backend auto-create it on next startup).*

---

## ⚙️ Configuration Cheat Sheet (`.env`)

Edit `.env` at any time to adjust settings:
```env
# Toggle dry-run mode (true = record proposals without writing; false = live writes)
DRY_RUN=true

# Show or hide browser window (true = background; false = visible Chrome window)
HEADLESS_BROWSER=false

# GitHub API token (already configured)
GITHUB_TOKEN=github_pat_...

# Instahyre Credentials (fill when ready for automated login)
INSTAHYRE_EMAIL=
INSTAHYRE_PASSWORD=
```
