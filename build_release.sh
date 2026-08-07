#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Harvest Hero — Release Builder
#
#  Run this whenever you want to create a new distributable:
#    chmod +x build_release.sh   (first time only)
#    ./build_release.sh
#
#  Output:  dist/HarvestHero-release/
#           └─ HarvestHero.app      ← the macOS app bundle (right-click / open)
#           └─ setup_client.py      ← LAN setup wizard
#           └─ HOW_TO_START.txt     ← end-user instructions
#
#  Zip that folder and send to users.
# ─────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Harvest Hero — Release Builder     ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# 1. Virtual environment
if [ ! -d ".venv" ]; then
    echo "[build] Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 2. Dependencies + PyInstaller
echo "[build] Installing dependencies..."
pip install -q -r requirements.txt
pip install -q pyinstaller

# 3. Generate icon files
echo "[build] Generating icons..."
python make_icons.py <<< "n"   # pass "n" to skip the build prompt inside make_icons

# 4. PyInstaller build
echo "[build] Building executable..."
python -m PyInstaller \
    --onefile \
    --windowed \
    --icon=assets/icon.icns \
    --name HarvestHero \
    --collect-data customtkinter \
    --add-data "assets:assets" \
    --noconfirm \
    main.py
# NOTE: do NOT --add-data data/inventory.db — that would ship the
# developer's local database (password hashes, real inventory) to every
# customer. The app creates a fresh DB in USER_DIR on first launch.

# 5. Assemble release folder
RELEASE="dist/HarvestHero-release"
echo "[build] Assembling release package..."
rm -rf "$RELEASE"
mkdir -p "$RELEASE"

cp -R dist/HarvestHero.app       "$RELEASE/"
cp setup_client.py             "$RELEASE/"
cp HOW_TO_START.txt            "$RELEASE/"

# 6. Create zip
ZIP="dist/HarvestHero-$(date +%Y%m%d).zip"
cd dist
zip -ry "../$ZIP" HarvestHero-release/
cd ..

echo ""
echo "  ✓ Build complete!"
echo "    App bundle : $RELEASE/HarvestHero.app"
echo "    Zip to send: $ZIP"
echo ""
echo "  Send the ZIP to end users."
echo "  They unzip it, right-click HarvestHero.app, and choose Open."
echo ""
