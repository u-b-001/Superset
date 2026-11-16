@echo off
title SamarthX Live Query & Security Audit Terminal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0open_query_terminal.ps1"
pause
