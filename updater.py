"""updater.py — Check a remote manifest to see if a newer build exists.

Option-2 update strategy: we do NOT download or apply anything. We just
tell the user "version X.Y is available, here's the download URL" so
they can grab the new bundle. The manifest format is intentionally a
superset of what a future auto-apply implementation will need
(`signature`, checksum fields), so bumping the client to option 3
later won't require a manifest migration.

The check runs in a background thread from app_window so the main Tk
loop is never blocked; the result is delivered via a threading.Event
that the UI polls via after().
"""

from __future__ import annotations

import json
import platform
import re
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from version import DEFAULT_MANIFEST_URL, __version__


# Requests uses a dedicated session so we can lock down trust_env the
# same way api_client does: no .netrc, no proxy env, no surprises.
def _session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": f"HarvestHero/{__version__}",
        "Accept": "application/json",
    })
    return s


@dataclass
class UpdateInfo:
    current: str
    latest: str
    url: str
    notes: str = ""
    released_at: str = ""


def _semver_tuple(v: str) -> tuple:
    """Parse "1.2.3", "1.2.3-rc.1", "1.2" into a comparable tuple.

    Anything that doesn't look remotely like a version sorts to (0,)
    so it never counts as "newer" than the running build.
    """
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?", v.strip())
    if not m:
        return (0,)
    parts = tuple(int(g or 0) for g in m.groups())
    return parts


def _pick_url(manifest: dict) -> str:
    """Pick the platform-specific download URL if present, otherwise
    fall back to the generic `url` field."""
    if sys.platform == "darwin":
        return manifest.get("url_mac") or manifest.get("url") or ""
    if sys.platform == "win32":
        return manifest.get("url_windows") or manifest.get("url") or ""
    return manifest.get("url_linux") or manifest.get("url") or ""


def fetch_manifest(url: str, timeout: float = 5.0) -> Optional[dict]:
    """Return the parsed manifest dict, or None if we can't reach the
    server / the response isn't valid JSON. Never raises."""
    try:
        r = _session().get(url, timeout=timeout)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def check_for_update(manifest_url: str = DEFAULT_MANIFEST_URL,
                     current_version: str = __version__) -> Optional[UpdateInfo]:
    """Return an UpdateInfo if the remote manifest advertises a version
    strictly greater than `current_version`; otherwise None."""
    manifest = fetch_manifest(manifest_url)
    if not manifest:
        return None

    latest = str(manifest.get("version", "")).strip()
    if not latest:
        return None
    if _semver_tuple(latest) <= _semver_tuple(current_version):
        return None

    url = _pick_url(manifest)
    if not url:
        return None

    return UpdateInfo(
        current=current_version,
        latest=latest,
        url=url,
        notes=str(manifest.get("notes") or ""),
        released_at=str(manifest.get("released_at") or ""),
    )


def check_async(callback: Callable[[Optional[UpdateInfo]], None],
                manifest_url: str = DEFAULT_MANIFEST_URL,
                current_version: str = __version__,
                delay_seconds: float = 0.0) -> None:
    """Fire-and-forget: run `check_for_update` on a daemon thread and
    invoke `callback(info)` from that thread when done. The Tk UI
    should not touch widgets from the callback directly — it should
    just flip a flag that a periodic after() poll picks up.

    A small startup `delay_seconds` avoids competing with the login
    round-trip and dashboard hydration on first launch.
    """
    def _worker():
        try:
            if delay_seconds:
                time.sleep(delay_seconds)
            info = check_for_update(manifest_url, current_version)
        except Exception:
            info = None
        try:
            callback(info)
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()
