@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .build-venv
if errorlevel 1 exit /b 1
.build-venv\Scripts\python -m pip install --disable-pip-version-check pyinstaller==6.11.1
if errorlevel 1 exit /b 1
.build-venv\Scripts\python -m PyInstaller --noconfirm --clean --onedir --windowed --name FolderAdjuster --icon assets\FolderAdjuster.ico --add-data "assets;assets" app.py
if errorlevel 1 exit /b 1
echo Created dist\FolderAdjuster\FolderAdjuster.exe
echo Distribute the entire FolderAdjuster folder, including _internal.
