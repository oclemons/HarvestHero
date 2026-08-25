@echo off
REM ─────────────────────────────────────────────────────────────
REM  Harvest Hero — Source ZIP Builder (Windows)
REM
REM  Produces HarvestHero-<VERSION>.zip containing ONLY tracked
REM  files from the git repo — no local secrets, no developer
REM  inventory database.
REM
REM  Usage:
REM    build_source_zip.bat
REM ─────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
    echo error: git is required
    exit /b 1
)

for /f "usebackq delims=" %%v in (`python -c "import json; print(json.load(open('VERSION.json'))['version'])"`) do set VERSION=%%v
set OUT=..\HarvestHero-%VERSION%.zip

echo [build] Packaging Harvest Hero v%VERSION%...
if exist "%OUT%" del "%OUT%"

git archive --format=zip --prefix=inventory_tracker/ -o "%OUT%" HEAD
if errorlevel 1 (
    echo error: git archive failed
    exit /b 1
)

echo.
echo   Built %OUT%
echo   Upload this ZIP as a GitHub Release asset for v%VERSION%.
