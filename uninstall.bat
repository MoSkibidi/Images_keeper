@echo off
rem Double-clickable wrapper around uninstall.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
