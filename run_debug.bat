@echo off
REM ─────────────────────────────────────────────────────────────
REM  Harvest Hero — Windows launcher (DEBUG MODE)
REM  This version keeps the console window open to show debug logs
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

REM 6. Launch in DEBUG MODE
echo.
echo [Harvest Hero] Starting in DEBUG MODE...
echo [Harvest Hero] Console will stay open to show debug messages
echo [Harvest Hero] Look for "DEBUG:" messages when testing
echo.
python main.py

REM Keep window open after app closes
echo.
echo [Harvest Hero] Application closed
echo Press any key to exit...
pause
