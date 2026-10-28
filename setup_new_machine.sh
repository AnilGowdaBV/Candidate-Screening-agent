#!/usr/bin/env bash
set -e

# ========================================================
#  Candidate Screening Agent - Automated Setup (macOS / Linux)
# ========================================================

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================"
echo " Candidate Screening Agent - Setup for macOS / Linux"
echo "========================================================"
echo ""

# 1. Detect Python 3.10+
echo "[1/5] Checking Python installation..."
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python is not installed or not in PATH!"
    echo "On macOS, install via Homebrew: brew install python@3.12"
    exit 1
fi

PY_VER=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PY_VER ($PYTHON_CMD)"

# 2. Check Node.js and npm
echo ""
echo "[2/5] Checking Node.js and npm..."
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] Node.js or npm is not installed!"
    echo "On macOS, install via Homebrew: brew install node"
    exit 1
fi
echo "Found Node $(node -v) and npm $(npm -v)"

# 3. Setup Backend Virtual Environment
echo ""
echo "[3/5] Setting up Python virtual environment (backend/venv)..."
if [ ! -d "backend/venv" ]; then
    $PYTHON_CMD -m venv backend/venv
fi

# Activate virtual environment
source backend/venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# 4. Install Playwright Chromium Browser
echo ""
echo "[4/5] Installing Playwright Chromium browser binaries..."
python -m playwright install chromium

# 5. Setup Frontend Dependencies
echo ""
echo "[5/5] Installing Frontend dependencies (npm install)..."
(cd frontend && npm install)

# 6. Setup .env file if missing
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example."
    fi
fi

echo ""
echo "========================================================"
echo " Setup Completed Successfully on macOS / Linux!"
echo " To start the application, run:"
echo "   ./start_agent.sh"
echo "========================================================"
