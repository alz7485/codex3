@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3.11 -m venv .venv
if not errorlevel 1 goto install
py -3.12 -m venv .venv
if not errorlevel 1 goto install
echo Python 3.11 or 3.12 is required. See README.md.
pause
exit /b 1

:install
if exist ".venv\.yohaku-ready" goto run
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo ready>".venv\.yohaku-ready"

:run
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo Could not start Yohaku. See the error above and README.md.
pause
exit /b 1
