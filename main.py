import json
import os
import secrets
import sys
from tkinter import messagebox

import customtkinter as ctk

from auth import hash_password
from database import Database
from login_screen import LoginScreen
from theme import apply_theme, BG_PRIMARY
from update_manager import get_update_manager
from update_dialog import show_update_notification

# Number of days of activity-log history to retain automatically.
ACTIVITY_LOG_RETENTION_DAYS = 30


def _fix_macos_app_name() -> None:
    """On macOS, running via `python main.py` shows 'python3.13' in the
    Dock / Cmd+Tab switcher instead of the app name (self.title() only
    affects the window titlebar, not the Dock). Rename the Cocoa bundle
    name so it reads 'Harvest Hero' instead. No-ops silently if pyobjc
    isn't installed, and isn't needed once packaged via PyInstaller
    (make_icons.py already sets --name HarvestHero for the built .app)."""
    if sys.platform != "darwin":
        return
    try:
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is not None:
            info["CFBundleName"] = "Harvest Hero"
    except Exception:
        pass


_fix_macos_app_name()
apply_theme()

from paths import USER_DIR
_CFG_PATH = os.path.join(USER_DIR, "config.json")


def _load_db():
    """Return the appropriate database backend based on config.json."""
    cfg = {}
    if os.path.exists(_CFG_PATH):
        with open(_CFG_PATH) as f:
            cfg = json.load(f)

    mode = cfg.get("mode", "local")

    if mode == "client":
        server_url = cfg.get("server_url", "http://localhost:5000")
        api_key = cfg.get("api_key", "")
        from api_client import ApiClient, ConnectionError as ApiError
        client = ApiClient(server_url, api_key=api_key)
        try:
            client.get_all_users()  # connectivity + token check
        except ApiError as e:
            messagebox.showerror("Cannot Connect to Server", str(e))
            sys.exit(1)
        return client, False  # (db, is_local)

    return Database(), True  # local mode


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Harvest Hero")
        self.geometry("1200x780")
        self.minsize(1000, 640)
        self._set_icon()

        self.db, is_local = _load_db()
        if is_local:
            self._ensure_default_admin()
        self._migrate_secrets()
        self._purge_old_activity_log()

        self.current_user = None
        self._frame = None
        self.update_manager = get_update_manager(
            os.path.dirname(os.path.abspath(__file__))
        )

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.show_login()
        
        # Check for updates after showing login screen
        self.after(2000, self._check_for_updates)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_icon(self) -> None:
        """Set the window icon from assets/HarvestHeroIcon.png."""
        try:
            from PIL import Image, ImageTk
            icon_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "assets", "HarvestHeroIcon.png",
            )
            if os.path.exists(icon_path):
                img = Image.open(icon_path).resize((256, 256))
                self._icon_ref = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, self._icon_ref)
        except Exception:
            pass

    def _ensure_default_admin(self) -> None:
        """Create a default admin account with a random password if no users exist yet."""
        if not self.db.get_all_users():
            random_pwd = secrets.token_urlsafe(12)
            pwd_hash, salt = hash_password(random_pwd)
            self.db.create_user("admin", pwd_hash, salt, "admin")
            messagebox.showinfo(
                "Default Admin Account Created",
                f"A default 'admin' account has been created.\n\n"
                f"Password: {random_pwd}\n\n"
                f"Please log in and reset this password immediately.",
            )

    def _migrate_secrets(self) -> None:
        """Encrypt any plaintext secrets left over in config.json from
        older versions of the app."""
        try:
            from ldap_auth import migrate_plaintext_password
            migrate_plaintext_password()
        except Exception:
            pass

    def _purge_old_activity_log(self) -> None:
        """Auto-purge activity log entries older than the retention window
        so history doesn't grow unbounded. Runs once per app startup."""
        try:
            self.db.clear_activity_log(older_than_days=ACTIVITY_LOG_RETENTION_DAYS)
        except Exception:
            pass

    def _swap_frame(self, new_frame: ctk.CTkFrame) -> None:
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_login(self) -> None:
        self.current_user = None
        self._swap_frame(LoginScreen(self, self._on_login_success))

    def _check_for_updates(self) -> None:
        """Check for updates in background."""
        def on_check_complete(has_update, version, notes):
            if has_update:
                show_update_notification(self, self.update_manager)
        
        self.update_manager.check_for_updates_async(on_check_complete)

    def _on_login_success(self, user: dict) -> None:
        self.current_user = user
        try:
            self.db.update_last_login(user["username"])
            self.db.log_activity(user["username"], "LOGIN",
                                 f"Role: {user['role']}")
        except Exception:
            pass
        from app_window import AppWindow
        self._swap_frame(AppWindow(self, user, self.db, self.show_login))


if __name__ == "__main__":
    app = App()
    app.mainloop()
