"""update_manager.py — GitHub-Release-driven update flow for Harvest Hero.

Behaviour depends on how the app is running:

* **Installed Windows build** (frozen exe from the Inno Setup installer):
  the "Update" button downloads the newest ``HarvestHeroSetup-*.exe``
  from the latest GitHub Release, verifies its SHA-256 against the
  release's ``.sha256`` sidecar, launches the installer with
  ``/SILENT /RESTARTAPPLICATIONS``, and exits the current process so
  the installer can replace the running binary. The installer then
  relaunches the new version. **User data lives outside {app} so it
  is never touched.**

* **Source install** (running ``python main.py`` on macOS or a dev
  Windows machine): the update mechanism still reports whether a
  newer release exists so devs know they're behind, but the "Install
  Update" action opens the release page in a browser rather than
  attempting an in-place upgrade. Devs pull from git or grab the
  installer manually.

The old flow (download a ZIP and overwrite files) is intentionally
gone — it stomped user data on source installs and never worked cleanly
on Windows for locked exes.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from typing import Callable, Optional, Tuple

import requests

# GitHub coordinates
GITHUB_OWNER = "oclemons"
GITHUB_REPO = "HarvestHero"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

VERSION_FILE = "VERSION.json"

# Windows installer naming convention emitted by the GitHub Actions
# workflow: HarvestHeroSetup-<version>.exe and .exe.sha256 sidecar.
INSTALLER_PREFIX = "HarvestHeroSetup"


def is_frozen_windows() -> bool:
    """Return True when running from the installed Windows exe."""
    return bool(getattr(sys, "frozen", False)) and sys.platform == "win32"


def _version_json_path() -> str:
    """Return the path to VERSION.json for the *running* build.

    In a PyInstaller onedir build, VERSION.json is bundled into the exe
    folder via the spec's ``datas``. In a source checkout it sits next
    to this file.
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, VERSION_FILE)


class UpdateManager:
    """Query GitHub for releases and, on Windows installs, apply them."""

    def __init__(self, app_root: Optional[str] = None):
        # app_root is retained for backwards compatibility with the old
        # ZIP-based flow but is no longer used to write anything into
        # the code folder.
        self.app_root = app_root or os.path.dirname(os.path.abspath(__file__))
        self.version_file = _version_json_path()
        self.current_version = self._load_version()
        self.latest_version: Optional[str] = None
        self.release_notes: str = ""
        self.installer_url: Optional[str] = None
        self.checksum_url: Optional[str] = None
        self.release_html_url: Optional[str] = None
        self.update_available = False

    # ------------------------------------------------------------------
    # Version handling
    # ------------------------------------------------------------------
    def _load_version(self) -> str:
        try:
            with open(self.version_file) as f:
                return json.load(f).get("version", "0.0.0")
        except Exception as exc:  # pragma: no cover
            print(f"[update] Could not read {self.version_file}: {exc}")
            return "0.0.0"

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Semantic-ish version comparison. Non-numeric suffixes are
        treated as pre-release and sort below their numeric root
        (2.1.0-rc1 < 2.1.0), which matches Inno Setup's ordering."""
        def parse(v: str):
            parts = []
            for chunk in v.lstrip("v").split("."):
                num = ""
                for ch in chunk:
                    if ch.isdigit():
                        num += ch
                    else:
                        break
                parts.append(int(num) if num else 0)
            return parts

        p1, p2 = parse(v1), parse(v2)
        while len(p1) < len(p2):
            p1.append(0)
        while len(p2) < len(p1):
            p2.append(0)
        for a, b in zip(p1, p2):
            if a < b: return -1
            if a > b: return 1
        return 0

    # ------------------------------------------------------------------
    # GitHub lookup
    # ------------------------------------------------------------------
    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Query GitHub for the latest release. Returns
        ``(update_available, latest_version, release_notes)``.
        """
        try:
            resp = requests.get(
                f"{GITHUB_API_URL}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
            resp.raise_for_status()
            release = resp.json()
        except Exception as exc:
            print(f"[update] check_for_updates failed: {exc}")
            return False, None, None

        tag = release.get("tag_name", "").lstrip("v")
        notes = release.get("body", "") or ""
        html_url = release.get("html_url")

        installer_url = None
        checksum_url = None
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            url = asset.get("browser_download_url")
            if not name or not url:
                continue
            if name.startswith(INSTALLER_PREFIX) and name.endswith(".exe"):
                installer_url = url
            elif name.startswith(INSTALLER_PREFIX) and name.endswith(".exe.sha256"):
                checksum_url = url

        self.release_html_url = html_url
        if not tag or self._compare_versions(self.current_version, tag) >= 0:
            self.update_available = False
            return False, None, None

        self.latest_version = tag
        self.release_notes = notes
        self.installer_url = installer_url
        self.checksum_url = checksum_url
        self.update_available = True
        return True, tag, notes

    def check_for_updates_async(self, callback: Callable) -> None:
        """Run ``check_for_updates`` off the UI thread."""
        def _run():
            has, ver, notes = self.check_for_updates()
            try:
                callback(has, ver, notes)
            except Exception as exc:  # pragma: no cover
                print(f"[update] callback error: {exc}")
        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Download + verify + install
    # ------------------------------------------------------------------
    def _temp_dir(self) -> str:
        d = os.path.join(tempfile.gettempdir(), "HarvestHero-update")
        os.makedirs(d, exist_ok=True)
        return d

    def download_installer(self, progress: Optional[Callable[[float], None]] = None
                           ) -> Tuple[bool, str]:
        """Download the installer (and its checksum sidecar) to a temp
        folder outside the app dir. Returns ``(ok, path_or_error)``.
        """
        if not self.installer_url:
            return False, "This release does not have a Windows installer attached."

        installer_path = os.path.join(
            self._temp_dir(), f"{INSTALLER_PREFIX}-{self.latest_version}.exe"
        )
        try:
            with requests.get(self.installer_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                seen = 0
                with open(installer_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        seen += len(chunk)
                        if progress and total:
                            progress((seen / total) * 100.0)
        except Exception as exc:
            return False, f"Download failed: {exc}"

        # Fetch the checksum sidecar. If it isn't there we refuse to
        # install rather than silently trust the download.
        if not self.checksum_url:
            return False, ("No SHA-256 checksum was attached to this release; "
                           "refusing to install for safety.")
        try:
            r = requests.get(self.checksum_url, timeout=15)
            r.raise_for_status()
            expected = r.text.split()[0].lower()
        except Exception as exc:
            return False, f"Could not fetch checksum: {exc}"

        actual = _sha256(installer_path)
        if actual != expected:
            try:
                os.remove(installer_path)
            except OSError:
                pass
            return False, ("Downloaded installer failed SHA-256 verification. "
                           f"expected {expected}, got {actual}")

        return True, installer_path

    def apply_update(self, installer_path: str) -> Tuple[bool, str]:
        """Launch the downloaded installer and exit the current app.

        The installer's ``CloseApplications=yes`` gives us a graceful
        window to shut down; we still ``sys.exit(0)`` explicitly so the
        installer can overwrite the exe without waiting.
        """
        if not is_frozen_windows():
            # A source install can't upgrade itself in place.
            return False, ("This is a developer build. Download the installer "
                           "manually from the Releases page to upgrade.")

        try:
            # /SILENT — small progress dialog, no wizard pages
            # /RESTARTAPPLICATIONS — relaunch the app when finished
            # /CLOSEAPPLICATIONS — offer to close running app cleanly
            subprocess.Popen(
                [installer_path, "/SILENT",
                 "/RESTARTAPPLICATIONS", "/CLOSEAPPLICATIONS"],
                shell=False,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
            )
        except Exception as exc:
            return False, f"Could not launch installer: {exc}"

        # Give the installer a beat to attach to our process, then quit.
        # Return True so the UI can show a "restarting" message; the
        # process itself will terminate before the caller uses it.
        threading.Timer(1.5, lambda: os._exit(0)).start()
        return True, f"Installing Harvest Hero {self.latest_version}…"

    def download_and_apply_async(
        self,
        progress_callback: Optional[Callable[[float], None]] = None,
        complete_callback: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        def _run():
            ok, result = self.download_installer(progress_callback)
            if not ok:
                if complete_callback:
                    complete_callback(False, result)
                return
            ok, msg = self.apply_update(result)
            if complete_callback:
                complete_callback(ok, msg)
        threading.Thread(target=_run, daemon=True).start()

    def open_release_page(self) -> None:
        """Fallback for devs: open the release page in a browser."""
        if self.release_html_url:
            try:
                webbrowser.open(self.release_html_url)
            except Exception:
                pass


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def get_update_manager(app_root: Optional[str] = None) -> UpdateManager:
    return UpdateManager(app_root)
