@echo off
title DermaInsight AI - Launcher
echo ===================================================
echo       Starting DermaInsight AI (PC Local Host)
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on Port 8000...
start "DermaInsight AI - Backend (Port 8000)" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting React Frontend on Port 3000...
start "DermaInsight AI - Frontend (Port 3000)" cmd /k "cd frontend && npm run dev -- --host 0.0.0.0 --port 3000"

echo.
echo ===================================================
echo Application is running!
echo Local PC: http://localhost:3000
echo Wi-Fi Network: http://192.168.0.196:3000
echo ===================================================
timeout /t 2 /nobreak >nul
start http://localhost:3000
