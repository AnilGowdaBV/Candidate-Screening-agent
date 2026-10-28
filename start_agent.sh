#!/usr/bin/env bash

# ========================================================
#  Candidate Screening Agent - Launcher (macOS / Linux)
# ========================================================

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================"
echo " Candidate Screening Agent - Starting Local Services"
echo "========================================================"
echo ""

# Verify environment
if [ ! -d "backend/venv" ] || [ ! -d "frontend/node_modules" ]; then
    echo "[!] Dependencies not found. Running first-time setup..."
    bash ./setup_new_machine.sh
fi

# Cleanup handler on exit or Ctrl+C
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null || true
    wait $(jobs -p) 2>/dev/null || true
    echo "Candidate Screening Agent stopped."
}
trap cleanup EXIT INT TERM

# 1. Start Backend
echo "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..."
PYTHONPATH=backend ./backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# 2. Start Frontend
echo "[2/2] Starting Vite React Frontend on http://127.0.0.1:5173 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

# 3. Wait briefly and auto-open browser on macOS / Linux
sleep 2
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://localhost:5173" 2>/dev/null || true
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:5173" 2>/dev/null || true
fi

echo ""
echo "========================================================"
echo " All services running!"
echo " UI:      http://localhost:5173"
echo " Backend: http://localhost:8000/docs"
echo " Press Ctrl+C at any time to stop all services."
echo "========================================================"
echo ""

wait
