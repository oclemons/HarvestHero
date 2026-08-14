"""update_dialog.py — Update notification and installation dialog.

Shows:
- Available update notification
- Release notes
- Download/install progress
- Restart prompt
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from update_manager import UpdateManager

from theme import (
    BG_PRIMARY, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)


class UpdateDialog(ctk.CTkToplevel):
    """Dialog for displaying and managing updates."""

    def __init__(self, parent, update_manager: UpdateManager):
        super().__init__(parent)
        self.update_manager = update_manager
        self.title("Update Available")
        self.geometry("600x500")
        self.resizable(True, True)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the update dialog."""
        # Title
        ctk.CTkLabel(
            self, text="🔄 Update Available",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 10))

        # Version info
        version_text = f"New version {self.update_manager.latest_version} is available"
        ctk.CTkLabel(
            self, text=version_text,
            font=ctk.CTkFont(size=12),
            text_color=ACCENT_GREEN,
        ).pack(pady=(0, 20))

        # Release notes
        ctk.CTkLabel(
            self, text="Release Notes:",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(10, 5))

        notes_frame = ctk.CTkFrame(self)
        notes_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        notes_text = ctk.CTkTextbox(notes_frame)
        notes_text.pack(fill="both", expand=True)
        notes_text.insert("1.0", self.update_manager.release_notes or "No release notes available")
        notes_text.configure(state="disabled")

        # Progress bar (initially hidden)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            self.progress_frame, text="Download Progress:",
            font=ctk.CTkFont(size=10),
        ).pack(anchor="w")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        self.progress_bar.set(0)
        self.progress_frame.pack_forget()  # Hide initially

        self.status_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
        )
        self.status_label.pack(pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="Install Update", width=140, height=40,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white",
            command=self._install_update,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Later", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        ).pack(side="right")

    def _install_update(self):
        """Start the update installation process."""
        # Show progress
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 10), before=self.status_label)
        
        # Disable button
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                widget.configure(state="disabled")

        def on_progress(progress):
            """Update progress bar."""
            self.progress_bar.set(progress / 100)
            self.status_label.configure(text=f"Downloading... {progress:.0f}%")
            self.update()

        def on_complete(success, message):
            """Handle completion."""
            if success:
                self.status_label.configure(
                    text="Update installed successfully!",
                    text_color=ACCENT_GREEN
                )
                messagebox.showinfo(
                    "Update Complete",
                    f"{message}\n\nThe application will restart now."
                )
                # Restart the app
                self.update_manager.restart_app()
            else:
                self.status_label.configure(
                    text=f"Error: {message}",
                    text_color=ACCENT_RED
                )
                messagebox.showerror("Update Failed", message)
                # Re-enable buttons
                for widget in self.winfo_children():
                    if isinstance(widget, ctk.CTkButton):
                        widget.configure(state="normal")

        # Download and apply in background
        self.update_manager.download_and_apply_async(on_progress, on_complete)


class UpdateCheckDialog(ctk.CTkToplevel):
    """Dialog shown while checking for updates."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Checking for Updates")
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the checking dialog."""
        ctk.CTkLabel(
            self, text="🔄 Checking for Updates",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            self, text="Please wait...",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).pack(pady=(0, 20))

        # Progress indicator
        progress = ctk.CTkProgressBar(self, indeterminate_speed=1.0)
        progress.pack(padx=20, pady=(0, 20), fill="x")
        progress.start()


def show_update_notification(parent, update_manager: UpdateManager):
    """Show update notification dialog if update is available.
    
    Args:
        parent: Parent window
        update_manager: UpdateManager instance
        
    Returns:
        True if update dialog was shown, False otherwise
    """
    if update_manager.update_available:
        UpdateDialog(parent, update_manager)
        return True
    return False


def check_and_notify_updates(parent, app_root: str = None):
    """Check for updates and show notification if available.
    
    Args:
        parent: Parent window
        app_root: Application root directory
    """
    from update_manager import get_update_manager
    
    # Show checking dialog
    check_dialog = UpdateCheckDialog(parent)
    parent.update()

    def on_check_complete(has_update, version, notes):
        """Handle check completion."""
        check_dialog.destroy()
        
        if has_update:
            show_update_notification(parent, update_manager)
        else:
            messagebox.showinfo(
                "No Updates",
                f"You are running the latest version ({update_manager.current_version})"
            )

    # Get update manager and check
    update_manager = get_update_manager(app_root)
    update_manager.check_for_updates_async(on_check_complete)
