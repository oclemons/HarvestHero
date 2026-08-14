@echo off
REM deploy.bat - Windows deployment script for Harvest Hero

setlocal enabledelayedexpansion

echo.
echo 🌾 Harvest Hero - Windows Deployment Script
echo ============================================
echo.

if "%1"=="client" (
    echo Setting up Harvest Hero on client device...
    echo.
    
    REM Create application directory
    set APP_DIR=%USERPROFILE%\HarvestHero
    if not exist "!APP_DIR!" mkdir "!APP_DIR!"
    cd /d "!APP_DIR!"
    
    REM Check if already cloned
    if exist ".git" (
        echo Updating existing installation...
        git pull origin main
    ) else (
        echo Cloning from GitHub...
        git clone https://github.com/oclemons/HarvestHero.git .
    )
    
    REM Install dependencies
    echo.
    echo Installing dependencies...
    pip install -r requirements.txt
    
    REM Create data directory
    if not exist "data" mkdir data
    
    echo.
    echo ✓ Installation complete!
    echo.
    echo To start the application, run:
    echo   cd !APP_DIR!
    echo   python main.py
    echo.
    
) else if "%1"=="dev" (
    echo Building development package...
    echo.
    
    REM Check git status
    git status --porcelain > nul
    if not errorlevel 0 (
        echo Warning: Uncommitted changes detected
        echo Commit changes before building for production
        exit /b 1
    )
    
    echo Current version in VERSION.json:
    findstr "version" VERSION.json | findstr /v "app_name"
    
    echo.
    echo ✓ Development package ready
    echo.
    echo To deploy:
    echo   1. Commit all changes: git add -A ^&^& git commit -m "message"
    echo   2. Push to GitHub: git push origin main
    echo   3. Create a release on GitHub
    echo   4. Run on client: deploy.bat client
    echo.
    
) else if "%1"=="release" (
    echo Creating release package...
    echo.
    
    REM Get version from VERSION.json
    for /f "tokens=2 delims=: " %%A in ('findstr "version" VERSION.json ^| findstr /v "app_name" ^| findstr /v "last_updated"') do (
        set VERSION=%%A
        set VERSION=!VERSION:"=!
        set VERSION=!VERSION:,=!
        goto :version_found
    )
    
    :version_found
    echo Version: !VERSION!
    
    REM Create zip file
    set ZIP_FILE=HarvestHero-v!VERSION!.zip
    echo Creating !ZIP_FILE!...
    
    REM Note: Windows doesn't have built-in zip, so we'll provide instructions
    echo.
    echo ✓ To create release package:
    echo   1. Select all files except:
    echo      - .git folder
    echo      - __pycache__ folders
    echo      - *.pyc files
    echo      - data/inventory.db
    echo      - .env files
    echo   2. Right-click and "Send to" ^> "Compressed (zipped) folder"
    echo   3. Name it: HarvestHero-v!VERSION!.zip
    echo.
    echo Next steps:
    echo   1. Go to GitHub: https://github.com/oclemons/HarvestHero/releases
    echo   2. Create new release for tag v!VERSION!
    echo   3. Upload HarvestHero-v!VERSION!.zip as asset
    echo   4. Publish release
    echo.
    
) else (
    echo Usage: deploy.bat [command]
    echo.
    echo Commands:
    echo   client   - Deploy to client device (downloads from GitHub^)
    echo   dev      - Prepare development build
    echo   release  - Create release package for GitHub
    echo.
    echo Examples:
    echo   deploy.bat client    - Install on client device
    echo   deploy.bat dev       - Prepare for development
    echo   deploy.bat release   - Create release package
    echo.
)

endlocal
