@echo off
setlocal
cd /d "%~dp0"
docker compose -f compose.yaml -f compose.calibration.yaml up -d --wait --wait-timeout 360
if errorlevel 1 exit /b 1
echo Calibration website: http://localhost:5182/#/analysis?module=calibration
