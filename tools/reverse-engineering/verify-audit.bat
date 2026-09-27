@echo off
setlocal
python "%~dp0verify_audit.py" %*
set "audit_exit=%errorlevel%"
exit /b %audit_exit%
