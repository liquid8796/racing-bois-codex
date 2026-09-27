@echo off
setlocal
cd /d "%~dp0\..\..\.."
python tools\p01\logic\emulate_fixtures.py
if errorlevel 1 exit /b 1
python tools\p01\logic\ai_fixtures.py
if errorlevel 1 exit /b 1
python tools\p01\logic\validate_native_contacts.py
if errorlevel 1 exit /b 1
python tools\p01\logic\verify_p01.py
exit /b %errorlevel%
