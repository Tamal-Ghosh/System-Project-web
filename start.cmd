@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker\start-segmentation.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. Read the message above.
  pause
  exit /b 1
)
exit /b 0
