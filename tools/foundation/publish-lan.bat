@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish-lan.ps1" %*
exit /b %ERRORLEVEL%
