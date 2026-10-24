@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto localpython
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 goto python311
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 goto python312
echo Python 3.11 or 3.12 is required. See README.md.
pause
exit /b 1

:localpython
".venv\Scripts\python.exe" scripts\build_onedir.py
if errorlevel 1 goto failed
goto ready

:python311
py -3.11 scripts\build_onedir.py
if errorlevel 1 goto failed
goto ready

:python312
py -3.12 scripts\build_onedir.py
if errorlevel 1 goto failed

:ready
echo Ready: dist\Yohaku\Yohaku.exe
echo ZIP: release\Yohaku-v0.18.3-windows-x64-onedir.zip
echo Distribute the whole onedir ZIP, not only the EXE.
pause
exit /b 0

:failed
echo Build failed. See the error above and README.md.
pause
exit /b 1
