@echo off
setlocal
pushd "%~dp0..\..\.."
if errorlevel 1 exit /b 1
python tools\p01\assets\decode_courses.py
if errorlevel 1 goto failed
python tools\p01\assets\decode_sprites.py
if errorlevel 1 goto failed
python tools\p01\assets\decode_media.py
if errorlevel 1 goto failed
python tools\p01\assets\complete_reference.py
if errorlevel 1 goto failed
python tools\p01\assets\close_rpth_legacy.py
if errorlevel 1 goto failed
python tools\p01\assets\unit_display.py
if errorlevel 1 goto failed
python tools\p01\assets\validate.py
if errorlevel 1 goto failed
popd
exit /b 0
:failed
popd
exit /b 1
