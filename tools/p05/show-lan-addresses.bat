@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0show-lan-addresses.ps1" %*
set "LAN_EXIT=%ERRORLEVEL%"
pause
exit /b %LAN_EXIT%
