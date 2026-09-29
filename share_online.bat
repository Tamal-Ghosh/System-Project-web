@echo off
title DermaInsight AI - Cloudflare Public Tunnel
echo =======================================================
echo          DermaInsight AI - Cloudflare Public Link
echo =======================================================
echo.
echo Starting Cloudflare HTTPS Tunnel...
echo (No password required! Anyone can access via the generated https:// link)
echo.
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --protocol http2 --url http://localhost:3000
pause
