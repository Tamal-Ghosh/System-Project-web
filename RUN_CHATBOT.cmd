@echo off
cd /d "%~dp0"
rem Stop earlier local preview containers before claiming their compatibility ports.
for %%C in (dermascope-e55-frontend-1 dermascope-e55-backend-1 dermascope-calibration-frontend-1 dermascope-calibration-backend-1) do (
  docker container inspect %%C >nul 2>&1
  if not errorlevel 1 docker stop %%C >nul
)
docker compose -f compose.yaml -f compose.chatbot.yaml up -d --wait --wait-timeout 360
if errorlevel 1 exit /b 1
echo Open http://localhost:5180/
