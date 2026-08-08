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

REM 5. (optional) Authenticode sign the .exe
REM
REM Skipped unless WINDOWS_SIGNING_CERT is set. Then the script hands
REM the .exe to signtool, timestamps against DigiCert's RFC 3161 server,
REM and verifies. See SIGNING.md for details.
REM
REM Required environment variables when signing:
REM   WINDOWS_SIGNING_CERT      Path to your .pfx / .p12 file, OR a
REM                             thumbprint of a cert already in the
REM                             LocalMachine\My store (recommended for
REM                             hardware EV tokens).
REM   WINDOWS_SIGNING_PASSWORD  Password protecting the .pfx (omit when
REM                             using a hardware token or a thumbprint).
REM Optional:
REM   WINDOWS_TIMESTAMP_URL     Defaults to DigiCert's RFC 3161 endpoint.
REM   SIGNTOOL_EXE              Full path to signtool.exe. Auto-detected
REM                             from the latest Windows SDK if omitted.

if not "%WINDOWS_SIGNING_CERT%"=="" (
    if "%WINDOWS_TIMESTAMP_URL%"=="" set "WINDOWS_TIMESTAMP_URL=http://timestamp.digicert.com"
    if "%SIGNTOOL_EXE%"=="" (
        for /f "delims=" %%p in ('where signtool 2^>nul') do set "SIGNTOOL_EXE=%%p"
    )
    if "%SIGNTOOL_EXE%"=="" (
        echo [sign] ERROR: signtool.exe not found. Install the Windows
        echo         SDK or set SIGNTOOL_EXE to its full path.
        exit /b 1
    )

    echo [sign] Signing HarvestHero.exe with %WINDOWS_SIGNING_CERT%...
    if "%WINDOWS_SIGNING_PASSWORD%"=="" (
        "%SIGNTOOL_EXE%" sign ^
            /f "%WINDOWS_SIGNING_CERT%" ^
            /tr "%WINDOWS_TIMESTAMP_URL%" /td sha256 /fd sha256 ^
            "dist\HarvestHero.exe"
    ) else (
        "%SIGNTOOL_EXE%" sign ^
            /f "%WINDOWS_SIGNING_CERT%" /p "%WINDOWS_SIGNING_PASSWORD%" ^
            /tr "%WINDOWS_TIMESTAMP_URL%" /td sha256 /fd sha256 ^
            "dist\HarvestHero.exe"
    )
    if errorlevel 1 (
        echo [sign] ERROR: signtool failed.
        exit /b 1
    )
    "%SIGNTOOL_EXE%" verify /pa "dist\HarvestHero.exe"
    echo [sign] Signed + verified.
) else (
    echo [sign] WINDOWS_SIGNING_CERT not set - shipping UNSIGNED.
    echo         Customers will see a SmartScreen warning on first launch.
    echo         See SIGNING.md when you're ready to obtain a certificate.
)

REM 6. Assemble release folder
set "RELEASE=dist\HarvestHero-release"
echo [build] Assembling release package...
rmdir /S /Q "%RELEASE%" 2>nul
mkdir "%RELEASE%"

copy "dist\HarvestHero.exe" "%RELEASE%\"
copy "setup_client.py" "%RELEASE%\"
copy "HOW_TO_START.txt" "%RELEASE%\"

REM 7. Create zip
for /f "usebackq" %%a in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd'"`) do set "MYDATE=%%a"
powershell -NoProfile -Command "Compress-Archive -Path '%RELEASE%' -DestinationPath 'dist\HarvestHero-%MYDATE%.zip' -Force"

echo.
echo   Build complete!
echo   Executable : %RELEASE%\HarvestHero.exe
echo   Zip to send: dist\HarvestHero-%MYDATE%.zip
echo.
if not "%WINDOWS_SIGNING_CERT%"=="" (
    echo   This build is signed. Customers just double-click the .exe.
) else (
    echo   This build is UNSIGNED. Customers must click "More info"
    echo   then "Run anyway" on the SmartScreen prompt.
)
echo.
pause
