@echo off
rem Double-clickable wrapper around install.ps1, so you don't need to open
rem PowerShell or type anything - just double-click this file in Explorer.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
