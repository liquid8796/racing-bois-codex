@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-lan.ps1" %*
set "LAN_EXIT=%ERRORLEVEL%"
if not "%LAN_EXIT%"=="0" pause
exit /b %LAN_EXIT%
