@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-native-lan.ps1" %*
exit /b %ERRORLEVEL%
