@echo off
title SamarthX - n8n Workflow Server (Port 5678)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_n8n.ps1"
pause

