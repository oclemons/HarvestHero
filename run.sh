#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Harvest Hero — Mac / Linux launcher
#  Run this file to start the application:
#    chmod +x run.sh   (first time only)
#    ./run.sh
# ─────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

# 1. Create / activate a virtual environment if one doesn't exist
if [ ! -d ".venv" ]; then
    echo "[Harvest Hero] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 2. Install / upgrade dependencies quietly
echo "[Harvest Hero] Checking dependencies..."
pip install -q -r requirements.txt

# 3. Generate icon files if they don't exist yet
if [ ! -f "assets/icon.icns" ]; then
    echo "[Harvest Hero] Building icon files..."
    python make_icons.py
fi

# 4. First-run client setup hint
if [ ! -f "config.json" ]; then
    echo ""
    echo "  TIP: If this PC should connect to a shared server,"
    echo "       run  python setup_client.py  first."
    echo "  Press Enter to continue in local mode, or Ctrl+C to cancel."
    read
fi

# 5. Launch the app
echo "[Harvest Hero] Starting..."
python main.py
