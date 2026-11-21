@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0backend\model.local.json" (
  echo Backend model config not found: backend\model.local.json
  echo Configure the local E38 model paths before using this launcher.
  pause
  exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
  echo Frontend packages are missing.
  echo Run: cd frontend ^&^& npm.cmd install
  pause
  exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo Node.js and npm are required for the frontend.
  pause
  exit /b 1
)

echo Starting the local E38 backend and Vite frontend...
echo Close the two opened terminal windows to stop the services.
echo If either port is already in use, stop the existing service first.

start "DermaScope Backend - API 8000" /D "%~dp0" powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -File "%~dp0run_inference.ps1"
start "DermaScope Frontend - Vite 5173" /D "%~dp0frontend" cmd.exe /K "npm.cmd run dev -- --port 5173"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173/"
exit /b 0
