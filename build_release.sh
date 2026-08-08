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

# 5. (optional) Code sign + notarize the .app
#
# Skipped entirely unless APPLE_DEVELOPER_ID is set. Then the script
# codesigns the bundle, submits it to Apple's notary service, and
# staples the ticket so first-launch on a customer's Mac shows no
# Gatekeeper warning.
#
# Required environment variables when signing:
#   APPLE_DEVELOPER_ID      "Developer ID Application: Your Name (TEAMID)"
#                           — paste exactly as `security find-identity -v` prints it.
#   APPLE_NOTARY_PROFILE    A keychain profile name you set up once with
#                           `xcrun notarytool store-credentials`.
#                           See SIGNING.md.
#
# Optional:
#   APPLE_ENTITLEMENTS      Path to an entitlements.plist. Defaults to
#                           none (Tk apps don't need any yet).
if [ -n "$APPLE_DEVELOPER_ID" ]; then
    echo "[sign] Codesigning HarvestHero.app as: $APPLE_DEVELOPER_ID"
    SIGN_ARGS=(--force --deep --options runtime --timestamp
               --sign "$APPLE_DEVELOPER_ID")
    if [ -n "$APPLE_ENTITLEMENTS" ] && [ -f "$APPLE_ENTITLEMENTS" ]; then
        SIGN_ARGS+=(--entitlements "$APPLE_ENTITLEMENTS")
    fi
    codesign "${SIGN_ARGS[@]}" dist/HarvestHero.app
    codesign --verify --deep --strict --verbose=2 dist/HarvestHero.app

    if [ -n "$APPLE_NOTARY_PROFILE" ]; then
        NOTARY_ZIP="dist/HarvestHero-notary.zip"
        echo "[sign] Creating temp zip for notarization..."
        ditto -c -k --keepParent dist/HarvestHero.app "$NOTARY_ZIP"
        echo "[sign] Submitting to Apple notary service (may take a few minutes)..."
        xcrun notarytool submit "$NOTARY_ZIP" \
            --keychain-profile "$APPLE_NOTARY_PROFILE" \
            --wait
        rm -f "$NOTARY_ZIP"
        echo "[sign] Stapling notarization ticket..."
        xcrun stapler staple dist/HarvestHero.app
        xcrun stapler validate dist/HarvestHero.app
        echo "[sign] ✓ Signed + notarized + stapled."
    else
        echo "[sign] APPLE_NOTARY_PROFILE not set — skipping notarization."
        echo "       The app is signed but customers will still see a"
        echo "       Gatekeeper prompt on first launch. See SIGNING.md."
    fi
else
    echo "[sign] APPLE_DEVELOPER_ID not set — shipping UNSIGNED."
    echo "       Customers will see a Gatekeeper warning on first launch."
    echo "       See SIGNING.md when you're ready to obtain a certificate."
fi

# 6. Assemble release folder
RELEASE="dist/HarvestHero-release"
echo "[build] Assembling release package..."
rm -rf "$RELEASE"
mkdir -p "$RELEASE"

cp -R dist/HarvestHero.app       "$RELEASE/"
cp setup_client.py             "$RELEASE/"
cp HOW_TO_START.txt            "$RELEASE/"

# 7. Create zip
ZIP="dist/HarvestHero-$(date +%Y%m%d).zip"
cd dist
zip -ry "../$ZIP" HarvestHero-release/
cd ..

echo ""
echo "  ✓ Build complete!"
echo "    App bundle : $RELEASE/HarvestHero.app"
echo "    Zip to send: $ZIP"
echo ""
if [ -n "$APPLE_DEVELOPER_ID" ]; then
    echo "  This build is signed. Customers just double-click the .app."
else
    echo "  This build is UNSIGNED. On first launch customers must"
    echo "  right-click HarvestHero.app → Open (or run once from"
    echo "  System Settings → Privacy & Security)."
fi
echo ""
