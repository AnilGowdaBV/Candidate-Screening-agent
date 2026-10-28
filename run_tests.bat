@echo off
title Candidate Screening Agent - Test Suite
echo ========================================================
echo  Running Candidate Screening Agent Test Suite
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Running Backend Pytest Suite (37 tests)...
backend\venv\Scripts\python.exe -m pytest -v
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Backend tests failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Running Frontend Strict TypeScript Build Check...
cd frontend
call npm.cmd run build
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Frontend build check failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo  ALL TESTS AND TYPE CHECKS PASSED SUCCESSFULLY!
echo ========================================================
pause
