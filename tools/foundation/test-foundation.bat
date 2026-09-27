@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0test-foundation.ps1" %*
exit /b %ERRORLEVEL%
