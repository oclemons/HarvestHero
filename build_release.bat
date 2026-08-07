@echo off
REM ─────────────────────────────────────────────────────────────
REM  Harvest Hero — Windows Release Builder
REM
REM  Run this on a Windows PC to create a new distributable:
REM    double-click build_release.bat
REM
REM  Output:  dist\HarvestHero-release\
REM           └─ HarvestHero.exe      ← the executable (double-click to open)
REM           └─ setup_client.py      ← LAN setup wizard
REM           └─ HOW_TO_START.txt     ← end-user instructions
REM
REM  Zip that folder and send to users.
REM ─────────────────────────────────────────────────────────────

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo   ======================================
echo    Harvest Hero - Windows Release Builder
echo   ======================================
echo.

REM 1. Virtual environment
if not exist ".venv\" (
    echo [build] Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

REM 2. Dependencies + PyInstaller
echo [build] Installing dependencies...
pip install -q -r requirements.txt
pip install -q pyinstaller

REM 3. Generate icon files
echo [build] Generating icons...
if exist "assets\icon.ico" (
    echo [build] Icon files already exist.
) else (
    echo n | python make_icons.py
)

REM 4. PyInstaller build
echo [build] Building executable...
REM NOTE: do NOT --add-data data\inventory.db — that would ship the
REM developer's local database (password hashes, real inventory) to
REM every customer. The app creates a fresh DB in USER_DIR on first launch.
python -m PyInstaller --noconfirm --onefile --windowed ^
    --icon=assets\icon.ico ^
    --name HarvestHero ^
    --collect-data customtkinter ^
    --add-data "assets;assets" ^
    main.py

REM 5. Assemble release folder
set "RELEASE=dist\HarvestHero-release"
echo [build] Assembling release package...
rmdir /S /Q "%RELEASE%" 2>nul
mkdir "%RELEASE%"

copy "dist\HarvestHero.exe" "%RELEASE%\"
copy "setup_client.py" "%RELEASE%\"
copy "HOW_TO_START.txt" "%RELEASE%\"

REM 6. Create zip
for /f "usebackq" %%a in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd'"`) do set "MYDATE=%%a"
powershell -NoProfile -Command "Compress-Archive -Path '%RELEASE%' -DestinationPath 'dist\HarvestHero-%MYDATE%.zip' -Force"

echo.
echo   Build complete!
echo   Executable : %RELEASE%\HarvestHero.exe
echo   Zip to send: dist\HarvestHero-%MYDATE%.zip
echo.
echo   Send the ZIP to end users.
echo   They unzip it, double-click HarvestHero.exe, and they're in.
echo.
pause
