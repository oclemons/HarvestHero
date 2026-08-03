@echo off
REM ─────────────────────────────────────────────────────────────
REM  Harvest Hero — Windows launcher
REM  Double-click this file to start the application.
REM ─────────────────────────────────────────────────────────────

cd /d "%~dp0"

REM 1. Create virtual environment if it doesn't exist
if not exist ".venv\" (
    echo [Harvest Hero] Creating virtual environment...
    python -m venv .venv
)

REM 2. Activate
call .venv\Scripts\activate.bat

REM 3. Install / upgrade dependencies
echo [Harvest Hero] Checking dependencies...
pip install -q -r requirements.txt

REM 4. Generate icon files if they don't exist yet
if not exist "assets\icon.ico" (
    echo [Harvest Hero] Building icon files...
    python make_icons.py
)

REM 5. First-run client setup hint
if not exist "config.json" (
    echo.
    echo   TIP: If this PC should connect to a shared server,
    echo        run  python setup_client.py  first.
    echo   Press Enter to continue in local mode, or close this window to cancel.
    pause
)

REM 6. Launch
echo [Harvest Hero] Starting...
python main.py

pause
