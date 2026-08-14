"""
app_window.py — Main application shell.
Premium sidebar + swappable content. Scanner is the primary page.
Enhanced with premium glass effects and theme awareness.
"""

import datetime
import threading
import tkinter as tk

import customtkinter as ctk

from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_MUTED, ACCENT_GOLD,
    ACCENT_GREEN, ACCENT_RED,
    SECONDARY_ACCENT, SECONDARY_ACCENT_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE, SIDEBAR_W,
    # legacy aliases kept for other modules
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)
from glass_effects import create_glass_button
from glass_effects_premium import GlassEffectManager
from theme_environments import get_theme_environment

# (label, icon, page_key, admin_only, staff_visible)
_NAV_ITEMS = [
    ("Dashboard",   "⊡", "dashboard",   False, True),
    ("Intake",      "⬡", "scan",         False, True),
    ("Inventory",   "▤", "inventory",    False, False),  # admin only
    ("Clients",     "☺", "clients",      False, False),  # admin only
    ("History",     "≡", "history",      False, False),  # admin only
    ("Shopping List", "☐", "shopping",   False, False),  # admin only
    ("Weights",     "⚖", "weights",      False, False),  # admin only
    ("Reports",     "◫", "reports",      False, False),  # admin only
    ("AI Command",  "◉", "ai",           False, False),  # admin only
    ("Admin",       "⊞", "users",        True,  False),
    ("Environment", "▦", "environment",  True,  False),
    ("Settings",    "⚙", "settings",     False, True),
]


class _NavButton(ctk.CTkFrame):
    """Sidebar nav item with violet pill active state."""

    def __init__(self, parent, icon: str, label: str,
                 on_click, active: bool = False):
        super().__init__(parent, fg_color="transparent",
                         cursor="hand2", corner_radius=8)
        self._on_click = on_click
        self._active = False
        self._build(icon, label)
        self.set_active(active)
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        for w in self.winfo_children():
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _build(self, icon, label):
        self.grid_columnconfigure(1, weight=1)
        self._icon_lbl = ctk.CTkLabel(
            self, text=icon,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15),
            width=24,
        )
        self._icon_lbl.grid(row=0, column=0, padx=(12, 6), pady=9)
        self._text_lbl = ctk.CTkLabel(
            self, text=label, anchor="w",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
        )
        self._text_lbl.grid(row=0, column=1, pady=9, padx=(0, 12), sticky="w")

    def set_active(self, active: bool):
        self._active = active
        if active:
            # Active state: Level 2 Reflective Glass effect with accent color
            self.configure(fg_color=ACCENT_MUTED,
                           border_width=2,
                           border_color=ACCENT,
                           corner_radius=10)
            self._icon_lbl.configure(text_color=ACCENT)
            self._text_lbl.configure(
                text_color=ACCENT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            )
        else:
            self.configure(fg_color="transparent", border_width=0, corner_radius=8)
            self._icon_lbl.configure(text_color=TEXT_MUTED)
            self._text_lbl.configure(
                text_color=TEXT_SECONDARY,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            )

    def _on_enter(self, _=None):
        if not self._active:
            # Hover state: Level 2 Reflective Glass effect with subtle depth
            self.configure(fg_color=BG_HOVER,
                           border_width=1,
                           border_color=BORDER_COLOR,
                           corner_radius=10)
            self._icon_lbl.configure(text_color=TEXT_PRIMARY)

    def _on_leave(self, _=None):
        if not self._active:
            self.configure(fg_color="transparent", border_width=0)
            self._icon_lbl.configure(text_color=TEXT_MUTED)

    def _click(self, _e=None):
        self._on_click()


class AppWindow(ctk.CTkFrame):
    """
    Main application frame — shown after successful login.
    Hosts: sidebar | content area | footer.
    """

    def __init__(self, parent, user: dict, db, on_logout):
        super().__init__(parent, fg_color=BG_PRIMARY, corner_radius=0)
        self.user = user
        self.db = db
        self.on_logout = on_logout
        self._page_cache: dict = {}
        self._current_page: str = ""
        self._nav_btns: dict = {}
        self._session_terminated = False
        self._pending_update = None  # populated by updater worker thread
        self._shutdown = threading.Event()  # tells background workers we're going away
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._build()
        self._start_clock()
        self._start_session_check()
        self._start_update_check()
        # Store reference on toplevel so quick actions can navigate
        try:
            parent.winfo_toplevel()._app_window = self
        except Exception:
            pass
        self.navigate("dashboard")
        # Launch tour for first-time users after the window is visible
        if not self.user.get("has_completed_tour", 0):
            self.after(600, self._launch_tour)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, minsize=SIDEBAR_W, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content()
        self._build_footer()

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")

        # ── Bottom: logout + user chip (packed first = anchors to bottom) ──
        # Use glass effect button for logout
        create_glass_button(
            sb, text="⏻  Log Out",
            command=self._logout,
            fg_color=BG_ELEVATED,
            hover_color=BG_HOVER,
            text_color=TEXT_MUTED,
            border_color=BORDER_COLOR,
        ).pack(side="bottom", fill="x", padx=14, pady=(4, 18))

        ctk.CTkLabel(
            sb, text="The Clemons Collective",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED,
        ).pack(side="bottom", pady=(0, 4))

        # Glass effect user chip
        user_chip = ctk.CTkFrame(
            sb, fg_color=BG_ELEVATED, corner_radius=8,
            border_width=1, border_color=BORDER_SUBTLE
        )
        user_chip.pack(side="bottom", fill="x", padx=14, pady=(0, 6))
        role_tag   = "Admin" if self.user["role"] == "admin" else "Staff"
        role_color = ACCENT_GOLD if self.user["role"] == "admin" else ACCENT_GREEN
        ctk.CTkLabel(
            user_chip, text=f"  {self.user['username']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).pack(side="left", padx=4, pady=8)
        ctk.CTkLabel(
            user_chip, text=role_tag,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=role_color,
        ).pack(side="right", padx=10)

        ctk.CTkFrame(sb, height=1, fg_color=BORDER_COLOR).pack(
            side="bottom", fill="x", padx=14, pady=(8, 4))

        # Update-available badge: hidden until the background check
        # discovers a newer manifest version. Packing it AFTER the
        # separator (still with side="bottom") makes it sit right below
        # the user chip when it appears.
        self._update_btn = ctk.CTkButton(
            sb, text="", height=28, corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=ACCENT_GOLD, hover_color=ACCENT_GOLD,
            text_color=BG_BASE, border_width=0,
            command=self._open_update_url,
        )
        # Not packed yet — _show_update_badge() calls .pack() when needed.
        self._update_url: str = ""

        # ── Top: logo with harvest theme ──
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.pack(side="top", fill="x", padx=18, pady=(26, 10))
        ctk.CTkLabel(
            brand, text="🌾",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20),
        ).pack(side="left", padx=(0, 8))
        logo_txt = ctk.CTkFrame(brand, fg_color="transparent")
        logo_txt.pack(side="left")
        ctk.CTkLabel(
            logo_txt, text="Harvest Hero",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_txt, text="Pantry Intelligence",
            font=ctk.CTkFont(family=FONT_FAMILY, size=8),
            text_color=TEXT_MUTED,
        ).pack(anchor="w")

        ctk.CTkFrame(sb, height=1, fg_color=BORDER_SUBTLE).pack(
            side="top", fill="x", padx=14, pady=(4, 10))

        # ── Nav buttons (scrollable so Settings is always reachable) ──
        nav = ctk.CTkScrollableFrame(
            sb, fg_color=BG_BASE, corner_radius=0,
            scrollbar_button_color=BORDER_COLOR,
            scrollbar_button_hover_color=BG_HOVER,
            label_text="",
        )
        nav.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 8))

        is_admin = self.user.get("role") == "admin"
        for label, icon, key, admin_only, staff_visible in _NAV_ITEMS:
            if admin_only and not is_admin:
                continue
            if not staff_visible and not is_admin:
                continue
            btn = _NavButton(
                nav, icon, label,
                on_click=lambda k=key: self.navigate(k),
            )
            btn.pack(side="top", fill="x", pady=1)
            self._nav_btns[key] = btn

    def _build_content(self):
        self._content = ctk.CTkFrame(self, fg_color=BG_PRIMARY, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

    def _build_footer(self):
        footer = ctk.CTkFrame(
            self, height=28, fg_color=BG_BASE, corner_radius=0)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        self._conn_lbl = ctk.CTkLabel(
            footer, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=ACCENT_GREEN,
        )
        self._conn_lbl.grid(row=0, column=1, pady=4)
        self._update_conn_status()

        self._clock_lbl = ctk.CTkLabel(
            footer, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self._clock_lbl.grid(row=0, column=2, padx=16, pady=4, sticky="e")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, page_key: str):
        if page_key == self._current_page:
            return

        # Update nav active state
        for key, btn in self._nav_btns.items():
            btn.set_active(key == page_key)

        # Remove current page
        for w in self._content.winfo_children():
            w.grid_forget()

        # Load / cache page
        if page_key not in self._page_cache:
            self._page_cache[page_key] = self._create_page(page_key)

        page = self._page_cache[page_key]
        if page:
            page.grid(row=0, column=0, sticky="nsew")
            if hasattr(page, "on_shown"):
                page.on_shown()

        self._current_page = page_key

    def _create_page(self, key: str):
        """Lazy-import and instantiate each page."""
        try:
            if key == "dashboard":
                if self.user.get("role") == "admin":
                    from admin_dashboard import AdminDashboard
                    return AdminDashboard(self._content, self.db, self.user,
                                         navigate=self.navigate)
                else:
                    from staff_dashboard import StaffDashboard
                    return StaffDashboard(self._content, self.db, self.user,
                                         navigate=self.navigate)
            if key == "scan":
                from intake_screen_pos import IntakeScreenPOS
                return IntakeScreenPOS(self._content, self.db, self.user)
            if key == "inventory":
                from inventory_list import InventoryList
                return InventoryList(self._content, self.db, self.user,
                                     embedded=True)
            if key == "clients":
                from client_management import ClientManagement
                return ClientManagement(self._content, self.db, self.user,
                                        embedded=True)
            if key == "history":
                from transaction_history import TransactionHistory
                return TransactionHistory(self._content, self.db, embedded=True)
            if key == "shopping":
                from shopping_list_screen import ShoppingListScreen
                return ShoppingListScreen(self._content, self.db, embedded=True)
            if key == "weights":
                from weight_management_screen import WeightManagementScreen
                return WeightManagementScreen(self._content, self.db, self.user, on_update=self._refresh_current_page)
            if key == "reports":
                from reports import Reports
                return Reports(self._content, self.db, embedded=True)
            if key == "ai":
                from ai_assistant import AIAssistant
                return AIAssistant(self._content, self.db)
            if key == "users":
                from user_management import UserManagement
                return UserManagement(self._content, self.db, self.user, embedded=True)
            if key == "environment":
                from env_dashboard import EnvDashboard
                return EnvDashboard(self._content, self.db, self.user)
            if key == "archive":
                from archive_manager import ArchiveManager
                return ArchiveManager(self._content, self.db, self.user, embedded=True)
            if key == "barcodes":
                from barcode_review import BarcodeReviewFrame
                return BarcodeReviewFrame(self._content)
            if key == "settings":
                from settings_screen import SettingsScreen
                return SettingsScreen(self._content, self.db, self.user)
        except Exception as exc:
            return self._placeholder(key, str(exc))

    def _placeholder(self, key: str, err: str = ""):
        frame = ctk.CTkFrame(self._content, fg_color=BG_PRIMARY)
        ctk.CTkLabel(
            frame,
            text=f"{key.upper()} PAGE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(expand=True)
        if err:
            ctk.CTkLabel(
                frame, text=err,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=ACCENT_RED, wraplength=600,
            ).pack(padx=40)
        return frame

    # ------------------------------------------------------------------
    # Footer utilities
    # ------------------------------------------------------------------

    def _update_conn_status(self):
        try:
            import json, os
            from paths import USER_DIR
            cfg_path = os.path.join(USER_DIR, "config.json")
            mode = "local"
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    mode = json.load(f).get("mode", "local")
            if mode == "local":
                self._conn_lbl.configure(
                    text="● Local Database", text_color=ACCENT_GREEN)
            else:
                self._conn_lbl.configure(
                    text="● LAN Server", text_color=ACCENT_GOLD)
        except Exception:
            self._conn_lbl.configure(
                text="● Unknown", text_color=TEXT_MUTED)

    def _start_clock(self):
        def _tick():
            now = datetime.datetime.now().strftime("%a %b %d  %I:%M:%S %p")
            if self._clock_lbl.winfo_exists():
                self._clock_lbl.configure(text=now + "  ")
                self.after(1000, _tick)
        _tick()

    # ------------------------------------------------------------------
    # Session validity check
    # ------------------------------------------------------------------
    #
    # Re-read this user's row from the DB every 30 seconds. If an admin
    # has deactivated the account or changed their role, force logout so
    # they don't keep clicking admin actions in a stale UI.

    _SESSION_CHECK_MS = 30_000

    def _start_session_check(self):
        self.after(self._SESSION_CHECK_MS, self._check_session)

    def _check_session(self):
        """Kick off a background DB lookup and hand the result back to
        the main thread for widget updates.

        The DB call has a 6-second HTTP timeout in client mode, so
        running it on the Tk main thread would freeze the entire UI
        while the network hangs. Move it to a daemon thread and
        deliver via after(0, ...).
        """
        if self._session_terminated:
            return

        username = self.user["username"]

        def _worker():
            try:
                fresh = self.db.get_user(username)
                err = None
            except Exception as exc:  # noqa: BLE001
                fresh = None
                err = exc

            # If the app closed while our DB call was in-flight there's
            # no point poking at Tk widgets on the way out.
            if self._shutdown.is_set():
                return

            def _apply():
                try:
                    if not self.winfo_exists() or self._session_terminated:
                        return
                except Exception:
                    return
                self._apply_session_check_result(fresh, err)

            try:
                self.after(0, _apply)
            except Exception:
                # Tk 3.14 refuses cross-thread after() when the main
                # loop isn't running yet; nothing to do — the next
                # check tick will retry.
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_session_check_result(self, fresh, err) -> None:
        if err is not None:
            # Network hiccup or DB error — treat as transient and try
            # again next tick rather than kicking a legitimate user out.
            self.after(self._SESSION_CHECK_MS, self._check_session)
            return

        if fresh is None or not fresh.get("is_active"):
            self._terminate_session(
                "This account has been deactivated. Please contact an administrator."
            )
            return
        if fresh.get("role") != self.user.get("role"):
            self._terminate_session(
                "Your role was changed. Please sign in again to continue."
            )
            return

        # Refresh cached fields that aren't security-sensitive (name, tour flag)
        for key in ("full_name", "has_completed_tour"):
            if key in fresh:
                self.user[key] = fresh[key]

        self.after(self._SESSION_CHECK_MS, self._check_session)

    # ------------------------------------------------------------------
    # Update-available check
    # ------------------------------------------------------------------

    def _start_update_check(self) -> None:
        """Kick off a background updater manifest fetch. The worker
        thread sets self._pending_update; a poller on the Tk main
        thread picks it up and shows the badge."""
        try:
            from updater import check_async
            import json, os
            from paths import USER_DIR

            manifest_url = None
            cfg_path = os.path.join(USER_DIR, "config.json")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path) as f:
                        manifest_url = json.load(f).get("update_url")
                except Exception:
                    manifest_url = None

            def _on_result(info):
                # Called from the worker thread — do NOT touch widgets here.
                self._pending_update = info

            kwargs = {
                "delay_seconds": 3.0,
                "shutdown_event": self._shutdown,
            }
            if manifest_url:
                kwargs["manifest_url"] = manifest_url
            check_async(_on_result, **kwargs)
        except Exception:
            return

        # Poll for the result on the main thread.
        self.after(1500, self._poll_update)

    def _poll_update(self) -> None:
        info = self._pending_update
        if info is None:
            # Not yet — try again shortly.
            try:
                if self.winfo_exists():
                    self.after(1500, self._poll_update)
            except Exception:
                pass
            return
        try:
            if self.winfo_exists():
                self._show_update_badge(info)
        except Exception:
            pass

    def _show_update_badge(self, info) -> None:
        self._update_url = info.url
        self._update_btn.configure(
            text=f"↑ Update available: {info.latest}"
        )
        self._update_btn.pack(
            side="bottom", fill="x", padx=14, pady=(6, 4),
            before=None,  # sit above the user chip stack we packed earlier
        )

    def _open_update_url(self) -> None:
        if not self._update_url:
            return
        try:
            import webbrowser
            webbrowser.open(self._update_url, new=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Session termination
    # ------------------------------------------------------------------

    def _terminate_session(self, reason: str) -> None:
        self._session_terminated = True
        self._shutdown.set()
        try:
            from tkinter import messagebox
            messagebox.showinfo("Session ended", reason)
        except Exception:
            pass
        try:
            self._page_cache.clear()
        except Exception:
            pass
        self.on_logout()

    def _on_destroy(self, event) -> None:
        """Tell background worker threads (session check, update
        checker) that the AppWindow is going away so they don't try to
        deliver results into destroyed widgets."""
        # <Destroy> fires for every child widget too; only act on the
        # window itself.
        if event.widget is self:
            self._shutdown.set()
            self._session_terminated = True

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def _launch_tour(self):
        from onboarding_tour import OnboardingTour

        def _on_tour_complete():
            try:
                self.db.set_tour_complete(self.user["id"])
                self.user["has_completed_tour"] = 1
            except Exception:
                pass

        # Find the real Tk root
        root = self.winfo_toplevel()
        OnboardingTour(root, navigate_fn=self.navigate,
                       on_complete=_on_tour_complete)

    def _logout(self):
        self._shutdown.set()
        self._page_cache.clear()
        self.on_logout()
