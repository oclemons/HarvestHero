"""update_dialog.py — In-app update notification for Harvest Hero.

Displays release notes for the latest GitHub Release and, on installed
Windows builds, downloads and runs the Inno Setup installer with SHA-256
verification. On dev / source builds the primary action becomes
"Open Release Page" so developers upgrade by running the installer
manually or pulling from git.
"""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from update_manager import UpdateManager, is_frozen_windows

from theme import (
    ACCENT_GREEN, ACCENT_RED, TEXT_MUTED,
)


class UpdateDialog(ctk.CTkToplevel):
    """Update Available modal."""

    def __init__(self, parent, update_manager: UpdateManager):
        super().__init__(parent)
        self.update_manager = update_manager
        self.title("Update Available")
        self.geometry("600x520")
        self.resizable(True, True)
        self.grab_set()
        self._install_button: ctk.CTkButton | None = None
        self._later_button: ctk.CTkButton | None = None
        self._build()
        self.after(100, self.lift)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build(self):
        ctk.CTkLabel(
            self, text="🌾  Update Available",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            self,
            text=f"Version {self.update_manager.latest_version} is ready to install.\n"
                 f"You are currently on {self.update_manager.current_version}.",
            font=ctk.CTkFont(size=12),
            text_color=ACCENT_GREEN,
            justify="center",
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            self, text="Release notes",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=20)

        notes_frame = ctk.CTkFrame(self)
        notes_frame.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        notes_text = ctk.CTkTextbox(notes_frame, wrap="word")
        notes_text.pack(fill="both", expand=True)
        notes_text.insert("1.0", self.update_manager.release_notes
                          or "(no release notes attached)")
        notes_text.configure(state="disabled")

        # Progress bar — hidden until download starts.
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED,
        )

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        install_label, install_cmd = self._primary_action()
        self._install_button = ctk.CTkButton(
            btn_frame, text=install_label, width=170, height=40,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white", command=install_cmd,
        )
        self._install_button.pack(side="right", padx=(10, 0))

        self._later_button = ctk.CTkButton(
            btn_frame, text="Later", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        )
        self._later_button.pack(side="right")

    def _primary_action(self):
        """Choose the button label and behaviour based on build mode."""
        if is_frozen_windows() and self.update_manager.installer_url:
            return "Install Update", self._install_update
        # Dev / source install (or a release with no Windows installer)
        return "Open Release Page", self._open_release

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _show_progress_ui(self):
        self.progress_bar.pack(fill="x", padx=20, pady=(4, 0))
        self.status_label.pack(pady=(4, 12))

    def _install_update(self):
        self._show_progress_ui()
        self._install_button.configure(state="disabled")
        self._later_button.configure(state="disabled")
        self.status_label.configure(text="Preparing download…")

        def on_progress(pct: float):
            self.after(0, lambda: self._on_progress(pct))

        def on_complete(ok: bool, msg: str):
            self.after(0, lambda: self._on_complete(ok, msg))

        self.update_manager.download_and_apply_async(on_progress, on_complete)

    def _on_progress(self, pct: float):
        self.progress_bar.set(pct / 100.0)
        self.status_label.configure(text=f"Downloading… {pct:.0f}%")

    def _on_complete(self, ok: bool, message: str):
        if ok:
            self.status_label.configure(text=message, text_color=ACCENT_GREEN)
            messagebox.showinfo(
                "Restarting",
                f"{message}\n\nHarvest Hero will restart automatically "
                "when the installer finishes.",
            )
            # apply_update() will terminate the process shortly.
        else:
            self.status_label.configure(text=message, text_color=ACCENT_RED)
            messagebox.showerror("Update Failed", message)
            self._install_button.configure(state="normal")
            self._later_button.configure(state="normal")

    def _open_release(self):
        self.update_manager.open_release_page()
        self.destroy()


def show_update_notification(parent, update_manager: UpdateManager) -> bool:
    """Show the dialog if the manager knows an update is available."""
    if update_manager.update_available:
        UpdateDialog(parent, update_manager)
        return True
    return False
