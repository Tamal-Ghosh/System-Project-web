@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker\start.ps1"
exit /b %ERRORLEVEL%
