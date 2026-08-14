#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Harvest Hero — macOS/Linux launcher (DEBUG MODE)
# This version keeps the terminal window open to show debug logs
# ─────────────────────────────────────────────────────────────

cd "$(dirname "$0")"

# 1. Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[Harvest Hero] Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Activate
source .venv/bin/activate

# 3. Install / upgrade dependencies
echo "[Harvest Hero] Checking dependencies..."
pip install -q -r requirements.txt

# 4. Generate icon files if they don't exist yet
if [ ! -f "assets/icon.ico" ]; then
    echo "[Harvest Hero] Building icon files..."
    python3 make_icons.py
fi

# 5. First-run client setup hint
if [ ! -f "config.json" ]; then
    echo ""
    echo "  TIP: If this PC should connect to a shared server,"
    echo "       run  python setup_client.py  first."
    echo "  Press Enter to continue in local mode, or Ctrl+C to cancel."
    read -p "  "
fi

# 6. Launch in DEBUG MODE
echo ""
echo "[Harvest Hero] Starting in DEBUG MODE..."
echo "[Harvest Hero] Console will stay open to show debug messages"
echo "[Harvest Hero] Look for 'DEBUG:' messages when testing"
echo ""
python3 main.py

# Keep terminal open after app closes
echo ""
echo "[Harvest Hero] Application closed"
echo "Press any key to exit..."
read -p ""
