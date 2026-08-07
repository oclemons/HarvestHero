"""paths.py — Centralised directory constants for Harvest Hero.

All code should import paths and use these constants instead of
constructing file paths manually.  Directories are created automatically
on first import so the app is self-bootstrapping on a new machine.

When the app is packaged by PyInstaller (onefile), bundled assets live in
sys._MEIPASS.  User data (database, imports, exports) is kept in a
persistent platform-appropriate location and the bundled seed database is
copied there on first run.
"""

import os
import shutil
import sys

# ── PyInstaller runtime ────────────────────────────────────────────────────
_FROZEN = getattr(sys, "frozen", False)
_MEIPASS = getattr(sys, "_MEIPASS", "")


def _user_dir() -> str:
    """Return a persistent user-data folder."""
    if _FROZEN:
        if sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        elif sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    else:
        # Development: keep everything in the project root
        return os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "HarvestHero")


# App dir (bundled resources in a frozen build; project root otherwise)
if _FROZEN:
    APP_DIR = _MEIPASS or os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# User dir (database + input/output; persistent across app updates)
USER_DIR = _user_dir()

DATA_DIR   = os.path.join(USER_DIR, "data")      # database file
INPUT_DIR  = os.path.join(USER_DIR, "input")     # user-supplied import files
OUTPUT_DIR = os.path.join(USER_DIR, "output")    # all generated output

BACKUP_DIR = os.path.join(OUTPUT_DIR, "backups")
EXPORT_DIR = os.path.join(OUTPUT_DIR, "exports")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")

DB_PATH    = os.path.join(DATA_DIR, "inventory.db")

# ---------------------------------------------------------------------------
# Bootstrap — create every directory that does not yet exist
# ---------------------------------------------------------------------------

for _d in (DATA_DIR, INPUT_DIR, OUTPUT_DIR, BACKUP_DIR, EXPORT_DIR, REPORT_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------------------
# One-time migration: move inventory.db from the old app-root location
# ---------------------------------------------------------------------------

_legacy_db = os.path.join(APP_DIR, "inventory.db")
if os.path.exists(_legacy_db) and not os.path.exists(DB_PATH):
    shutil.move(_legacy_db, DB_PATH)

# ---------------------------------------------------------------------------
# Optional seed: copy a bundled starter database into the user-data dir
# on first launch.
#
# The release build scripts DO NOT include a seed DB by default — shipping
# the developer's inventory.db to every customer would leak password
# hashes and real data. This block stays here so a downstream integrator
# who intentionally adds `--add-data data/inventory.db:data` gets the
# expected one-time-seed behaviour. In normal releases it's a no-op.
# ---------------------------------------------------------------------------

if _FROZEN and _MEIPASS:
    _bundled_db = os.path.join(_MEIPASS, "data", "inventory.db")
    if os.path.exists(_bundled_db) and not os.path.exists(DB_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        shutil.copy2(_bundled_db, DB_PATH)
