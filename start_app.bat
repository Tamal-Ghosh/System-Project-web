@echo off
title DermaInsight AI - E38 Model Launcher
echo ===================================================
echo     Starting DermaInsight AI (E38 Model via Docker)
echo ===================================================
echo.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command "& { try { $v = docker info --format '{{.ServerVersion}}' 2>$null; if (-not $v) { throw 'Docker not running' } } catch { exit 1 } }"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker Desktop is not running!
    echo Please launch Docker Desktop, wait for it to start, and run this script again.
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting DermaInsight E38 containers...
call "%~dp0RUN_DOCKER.cmd"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Docker containers.
    pause
    exit /b %ERRORLEVEL%
)

echo [2/2] Opening application in browser...
timeout /t 2 /nobreak >nul
start http://localhost:5180

echo.
echo ===================================================
echo   Application is running!
echo   URL: http://localhost:5180
echo   To stop: run 'docker compose down'
echo ===================================================
timeout /t 5 >nul
