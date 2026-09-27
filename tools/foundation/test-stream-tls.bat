@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0test-stream-tls.ps1" %*
exit /b %ERRORLEVEL%
