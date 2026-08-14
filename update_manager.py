"""update_manager.py — Automatic update system for GitHub-based distribution.

Handles:
- Checking for updates on GitHub
- Downloading updates
- Applying updates with restart
- Version management
- Update notifications
"""

import os
import sys
import json
import subprocess
import threading
import requests
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional

# GitHub repository details
GITHUB_OWNER = "oclemons"
GITHUB_REPO = "HarvestHero"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

# Version file path
VERSION_FILE = "VERSION.json"


class UpdateManager:
    """Manages automatic updates from GitHub."""

    def __init__(self, app_root: str = None):
        """Initialize update manager.
        
        Args:
            app_root: Root directory of the application
        """
        self.app_root = app_root or os.path.dirname(os.path.abspath(__file__))
        self.version_file = os.path.join(self.app_root, VERSION_FILE)
        self.current_version = self._load_version()
        self.latest_version = None
        self.update_available = False
        self.update_url = None

    def _load_version(self) -> str:
        """Load current version from VERSION.json."""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    data = json.load(f)
                    return data.get("version", "1.0.0")
        except Exception as e:
            print(f"Error loading version: {e}")
        return "1.0.0"

    def _save_version(self, version: str):
        """Save version to VERSION.json."""
        try:
            data = {
                "version": version,
                "last_updated": datetime.now().isoformat(),
                "app_name": "Harvest Hero Inventory Tracker"
            }
            with open(self.version_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving version: {e}")

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check GitHub for new releases.
        
        Returns:
            Tuple of (update_available, latest_version, release_notes)
        """
        try:
            # Get latest release from GitHub
            response = requests.get(
                f"{GITHUB_API_URL}/releases/latest",
                timeout=10
            )
            response.raise_for_status()
            
            release = response.json()
            latest_version = release.get("tag_name", "").lstrip("v")
            release_notes = release.get("body", "")
            download_url = None
            
            # Get download URL for the release
            assets = release.get("assets", [])
            for asset in assets:
                if asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
            
            # Compare versions
            if self._compare_versions(self.current_version, latest_version) < 0:
                self.latest_version = latest_version
                self.update_url = download_url
                self.update_available = True
                return True, latest_version, release_notes
            
            return False, None, None
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return False, None, None

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings.
        
        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            
            # Pad with zeros
            while len(parts1) < len(parts2):
                parts1.append(0)
            while len(parts2) < len(parts1):
                parts2.append(0)
            
            for p1, p2 in zip(parts1, parts2):
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            return 0
        except Exception:
            return 0

    def download_update(self, callback=None) -> Tuple[bool, str]:
        """Download update from GitHub.
        
        Args:
            callback: Function to call with progress updates
            
        Returns:
            Tuple of (success, message)
        """
        if not self.update_url:
            return False, "No update URL available"
        
        try:
            # Create temp directory for download
            temp_dir = os.path.join(self.app_root, ".update_temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            zip_path = os.path.join(temp_dir, "update.zip")
            
            # Download the file
            response = requests.get(self.update_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            callback(progress)
            
            return True, zip_path
        except Exception as e:
            return False, f"Download failed: {str(e)}"

    def apply_update(self, zip_path: str) -> Tuple[bool, str]:
        """Extract and apply update.
        
        Args:
            zip_path: Path to downloaded update zip
            
        Returns:
            Tuple of (success, message)
        """
        try:
            import zipfile
            
            # Extract to temp location first
            temp_extract = os.path.join(self.app_root, ".update_extract")
            os.makedirs(temp_extract, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)
            
            # Find the actual source directory
            # GitHub releases typically have a top-level folder
            extracted_items = os.listdir(temp_extract)
            if len(extracted_items) == 1 and os.path.isdir(
                os.path.join(temp_extract, extracted_items[0])
            ):
                source_dir = os.path.join(temp_extract, extracted_items[0])
            else:
                source_dir = temp_extract
            
            # Backup current files
            backup_dir = os.path.join(self.app_root, ".backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copy new files over old ones
            for item in os.listdir(source_dir):
                src = os.path.join(source_dir, item)
                dst = os.path.join(self.app_root, item)
                
                # Skip certain directories
                if item in [".git", ".github", ".update_temp", ".update_extract", ".backup", "data"]:
                    continue
                
                if os.path.isdir(src):
                    # Copy directory
                    import shutil
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    # Copy file
                    import shutil
                    shutil.copy2(src, dst)
            
            # Update version file
            self._save_version(self.latest_version)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_extract, ignore_errors=True)
            os.remove(zip_path)
            
            return True, f"Update applied successfully. Version {self.latest_version}"
        except Exception as e:
            return False, f"Update failed: {str(e)}"

    def restart_app(self):
        """Restart the application."""
        try:
            # Get the main script path
            main_script = os.path.join(self.app_root, "main.py")
            
            if os.path.exists(main_script):
                # Restart with the same Python interpreter
                os.execl(sys.executable, sys.executable, main_script)
            else:
                print("main.py not found")
        except Exception as e:
            print(f"Error restarting app: {e}")

    def check_for_updates_async(self, callback=None):
        """Check for updates in background thread.
        
        Args:
            callback: Function to call with (has_update, version, notes)
        """
        def _check():
            has_update, version, notes = self.check_for_updates()
            if callback:
                callback(has_update, version, notes)
        
        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def download_and_apply_async(self, progress_callback=None, complete_callback=None):
        """Download and apply update in background thread.
        
        Args:
            progress_callback: Function to call with progress (0-100)
            complete_callback: Function to call with (success, message)
        """
        def _download_apply():
            try:
                # Download
                success, result = self.download_update(progress_callback)
                if not success:
                    if complete_callback:
                        complete_callback(False, result)
                    return
                
                zip_path = result
                
                # Apply
                success, message = self.apply_update(zip_path)
                if complete_callback:
                    complete_callback(success, message)
            except Exception as e:
                if complete_callback:
                    complete_callback(False, str(e))
        
        thread = threading.Thread(target=_download_apply, daemon=True)
        thread.start()


def get_update_manager(app_root: str = None) -> UpdateManager:
    """Get or create update manager instance."""
    return UpdateManager(app_root)
