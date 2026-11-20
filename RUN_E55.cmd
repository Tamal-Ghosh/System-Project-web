@echo off
cd /d "%~dp0"
docker compose -p dermascope-e55 -f compose.yaml -f compose.e55.yaml up -d
if errorlevel 1 exit /b 1
echo E55 website: http://localhost:5181/
