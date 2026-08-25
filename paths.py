"""paths.py — Centralised directory constants for Harvest Hero.

All code should import paths and use these constants instead of
constructing file paths manually.  Directories are created automatically
on first import so the app is self-bootstrapping on a new machine.

Data-persistence contract
-------------------------
User data (database, imports, exports, secrets) NEVER lives inside the
application folder. It lives in a persistent, platform-appropriate
user-data directory:

    macOS:   ~/Library/Application Support/HarvestHero
    Windows: %APPDATA%\\HarvestHero
    Linux:   $XDG_DATA_HOME/HarvestHero  (default ~/.local/share/HarvestHero)

This is true whether the app is running from source (`py main.py`) or
from a PyInstaller frozen build. Because the code folder and the data
folder are separate, a client can delete or re-extract the code folder
without touching a single row of their inventory, users, or settings.

On first launch after upgrading from an older release that stored data
inside the code folder, this module migrates the legacy files into the
persistent location. The migration only runs when the persistent
location has no database yet, so it can never overwrite newer data.

Developer override
------------------
Set the ``HARVESTHERO_DEV_DIR`` environment variable to an absolute path
to force user data into a project-local directory while developing.
Never set this on a client machine.
"""

import os
import shutil
import sys

# ── PyInstaller runtime ────────────────────────────────────────────────────
_FROZEN = getattr(sys, "frozen", False)
_MEIPASS = getattr(sys, "_MEIPASS", "")

_DEV_OVERRIDE = os.environ.get("HARVESTHERO_DEV_DIR", "").strip()


def _default_user_dir() -> str:
    """Return the platform-appropriate persistent user-data folder."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "HarvestHero")


def _user_dir() -> str:
    if _DEV_OVERRIDE:
        return os.path.abspath(_DEV_OVERRIDE)
    return _default_user_dir()


# App dir (bundled resources in a frozen build; project root otherwise).
# NEVER write user data here — it's replaced on every update.
if _FROZEN:
    APP_DIR = _MEIPASS or os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# User dir — persistent across app updates and re-extractions.
USER_DIR = _user_dir()

DATA_DIR   = os.path.join(USER_DIR, "data")      # database + secret_key
INPUT_DIR  = os.path.join(USER_DIR, "input")     # user-supplied import files
OUTPUT_DIR = os.path.join(USER_DIR, "output")    # generated output

BACKUP_DIR = os.path.join(OUTPUT_DIR, "backups")
EXPORT_DIR = os.path.join(OUTPUT_DIR, "exports")
REPORT_DIR = os.path.join(OUTPUT_DIR, "reports")

DB_PATH = os.path.join(DATA_DIR, "inventory.db")

# ---------------------------------------------------------------------------
# Bootstrap — create every directory that does not yet exist
# ---------------------------------------------------------------------------
for _d in (USER_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR, BACKUP_DIR, EXPORT_DIR, REPORT_DIR):
    os.makedirs(_d, exist_ok=True)


# ---------------------------------------------------------------------------
# One-time migration from legacy in-code-folder locations
# ---------------------------------------------------------------------------
def _migrate_legacy() -> None:
    """Move a client's data from the old (in-code-folder) location into
    the new persistent USER_DIR the first time the upgraded app runs.

    Runs only when the persistent DB does not yet exist, so it can never
    clobber newer data. Copies are used instead of moves for the DB so a
    failed migration leaves the client's original data intact; the
    legacy copy is renamed with a ``.migrated`` suffix once the new copy
    is in place, so subsequent runs skip it.
    """
    if _DEV_OVERRIDE:
        # A developer override deliberately points at a project-local
        # dir; skip migration so the dev's checkout stays predictable.
        return

    legacy_candidates = [
        os.path.join(APP_DIR, "data", "inventory.db"),
        os.path.join(APP_DIR, "inventory.db"),
    ]

    if not os.path.exists(DB_PATH):
        for legacy in legacy_candidates:
            if os.path.exists(legacy) and os.path.getsize(legacy) > 0:
                try:
                    shutil.copy2(legacy, DB_PATH)
                    # Rename rather than delete — keeps a local backup
                    # the client can point at if something looks wrong.
                    os.replace(legacy, legacy + ".migrated")
                    break
                except Exception as exc:  # pragma: no cover - best effort
                    print(f"[paths] Legacy DB migration failed for {legacy}: {exc}")

    # Migrate ancillary files (secret_key, sidecar dbs) if present and
    # not already in the persistent location.
    for name in (".secret_key", "t.db"):
        legacy = os.path.join(APP_DIR, "data", name)
        target = os.path.join(DATA_DIR, name)
        if os.path.exists(legacy) and not os.path.exists(target):
            try:
                shutil.copy2(legacy, target)
            except Exception as exc:  # pragma: no cover
                print(f"[paths] Legacy {name} migration failed: {exc}")


_migrate_legacy()


# ---------------------------------------------------------------------------
# Optional seed database (frozen builds only)
# ---------------------------------------------------------------------------
# Release builds intentionally DO NOT include the developer's inventory.db.
# If a downstream integrator adds `--add-data data/inventory.db:data` to
# their PyInstaller spec, the bundled DB is copied into the user-data
# dir on first launch — but only if the user does not already have one.
if _FROZEN and _MEIPASS:
    _bundled_db = os.path.join(_MEIPASS, "data", "inventory.db")
    if os.path.exists(_bundled_db) and not os.path.exists(DB_PATH):
        shutil.copy2(_bundled_db, DB_PATH)
