"""update_config.py — read the auto-update policy.

Precedence:
  1. ``<USER_DIR>/update_config.json`` — per-client override (persists
     across updates because USER_DIR is outside the code folder).
  2. ``<app>/update_config.json`` — the default shipped with the build.
  3. Hard-coded fallback in ``DEFAULTS`` below (also what you get if
     the file exists but is malformed).

Schema
------
* ``auto_update``            bool  master switch; everything else off if False
* ``check_on_startup``       bool  fire one check ~2 s after the app launches
* ``check_interval_hours``   int   recheck this often while the app is open;
                                   0 disables recurring rechecks
* ``notify_user``            bool  reserved for a future silent-install mode
* ``download_timeout``       int   per-request seconds cap on the installer
                                   download (currently unused by the manager,
                                   kept for forward compatibility)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict

try:
    from paths import USER_DIR
except Exception:  # pragma: no cover - only when paths hasn't imported yet
    USER_DIR = os.path.expanduser("~")

DEFAULTS: Dict = {
    "auto_update": True,
    "check_on_startup": True,
    "check_interval_hours": 6,
    "notify_user": True,
    "download_timeout": 300,
}


def _bundled_config_path() -> str:
    """Path to the config that ships inside the frozen build (or, in
    a source checkout, sits next to main.py)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "update_config.json")


def _user_config_path() -> str:
    return os.path.join(USER_DIR, "update_config.json")


def _read(path: str) -> Dict:
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, ValueError):
        return {}


def load() -> Dict:
    """Return the merged update-policy dict.

    Missing / malformed fields fall back to ``DEFAULTS``. Callers should
    treat unknown keys as harmless (forward compatibility).
    """
    cfg = dict(DEFAULTS)
    for path in (_bundled_config_path(), _user_config_path()):
        overrides = _read(path)
        if overrides:
            cfg.update(overrides)

    # Normalize types so bad hand-edits can't crash the app.
    cfg["auto_update"]         = bool(cfg.get("auto_update", True))
    cfg["check_on_startup"]    = bool(cfg.get("check_on_startup", True))
    cfg["notify_user"]         = bool(cfg.get("notify_user", True))
    try:
        cfg["check_interval_hours"] = max(0, int(cfg.get("check_interval_hours", 6)))
    except (TypeError, ValueError):
        cfg["check_interval_hours"] = DEFAULTS["check_interval_hours"]
    try:
        cfg["download_timeout"] = max(30, int(cfg.get("download_timeout", 300)))
    except (TypeError, ValueError):
        cfg["download_timeout"] = DEFAULTS["download_timeout"]
    return cfg
