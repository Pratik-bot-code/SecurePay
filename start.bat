@echo off
title SecurePay Launcher
cd /d "%~dp0"

echo ========================================================
echo   Starting SecurePay (Backend + Frontend)
echo ========================================================

echo [1/2] Launching Backend API on http://127.0.0.1:8000...
start "SecurePay Backend" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Launching Frontend Web on http://localhost:5173...
start "SecurePay Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo   SecurePay is now running!
echo   - Web Application: http://localhost:5173
echo   - Backend API:     http://127.0.0.1:8000
echo   - API Docs:        http://127.0.0.1:8000/api/docs
echo ========================================================
echo.
pause
