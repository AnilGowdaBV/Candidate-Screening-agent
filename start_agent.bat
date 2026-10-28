@echo off
title Candidate Screening Agent Launcher
echo ========================================================
echo  Candidate Screening Agent - Starting Local Services
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "Screening Agent - Backend" cmd /k "set PYTHONPATH=backend&& backend\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting Vite React Frontend on http://127.0.0.1:5173 ...
start "Screening Agent - Frontend" cmd /k "cd frontend && npm.cmd run dev"

echo.
echo ========================================================
echo  All services started!
echo  Open your browser to: http://localhost:5173
echo ========================================================
pause
