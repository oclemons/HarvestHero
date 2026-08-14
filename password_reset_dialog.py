"""password_reset_dialog.py — Password reset request dialog for staff.

Allows staff to request password reset from admin.
Only admins can set/reset passwords.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime

from theme import (
    BG_PRIMARY, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)


class PasswordResetDialog(ctk.CTkToplevel):
    """Dialog for requesting password reset."""

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Request Password Reset")
        self.geometry("500x400")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the dialog."""
        self.configure(fg_color=BG_SURFACE)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main frame
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        main.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            main, text="🔐 Request Password Reset",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Description
        ctk.CTkLabel(
            main, text="Contact your administrator to reset your password.\n\n"
                      "Only administrators can set or reset passwords.\n"
                      "This ensures account security.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 20))

        # Admin info section
        info_frame = ctk.CTkFrame(main, fg_color=BG_ELEVATED, corner_radius=8)
        info_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            info_frame, text="📋 Administrator Contacts",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ACCENT_GOLD,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 8))

        # Get admin users
        try:
            admins = self.db.get_users_by_role("admin")
            if admins:
                admin_text = "\n".join([
                    f"• {admin['full_name'] or admin['username']}"
                    for admin in admins
                ])
            else:
                admin_text = "• No administrators found"
        except Exception:
            admin_text = "• Unable to load administrator list"

        ctk.CTkLabel(
            info_frame, text=admin_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        # Security info
        security_frame = ctk.CTkFrame(main, fg_color=BG_ELEVATED, corner_radius=8)
        security_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        security_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            security_frame, text="🔒 Security Policy",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ACCENT_GREEN,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 8))

        security_text = (
            "✓ Only admins can set passwords\n"
            "✓ Passwords are never shared via email\n"
            "✓ Reset in person or via secure channel\n"
            "✓ All password changes are logged"
        )

        ctk.CTkLabel(
            security_frame, text=security_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="Close",
            height=40, corner_radius=8,
            fg_color=ACCENT, hover_color="#1d4ed8",
            text_color="white",
            command=self.destroy,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Copy Admin List",
            height=40, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self._copy_admin_list,
        ).pack(side="right")

    def _copy_admin_list(self):
        """Copy admin list to clipboard."""
        try:
            admins = self.db.get_users_by_role("admin")
            if admins:
                admin_text = "\n".join([
                    f"{admin['full_name'] or admin['username']}"
                    for admin in admins
                ])
                self.clipboard_clear()
                self.clipboard_append(admin_text)
                messagebox.showinfo(
                    "Copied",
                    "Administrator list copied to clipboard."
                )
            else:
                messagebox.showwarning(
                    "No Admins",
                    "No administrators found in the system."
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {str(e)}")


class AdminPasswordResetDialog(ctk.CTkToplevel):
    """Dialog for admin to reset a user's password."""

    def __init__(self, parent, db, username: str, on_reset=None):
        super().__init__(parent)
        self.db = db
        self.username = username
        self.on_reset = on_reset
        self.title(f"Reset Password - {username}")
        self.geometry("500x500")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the dialog."""
        self.configure(fg_color=BG_SURFACE)
        self.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            self, text=f"🔐 Reset Password for {self.username}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 8))

        # Description
        ctk.CTkLabel(
            self, text="Set a new temporary password for this user.\n"
                      "User should change it on first login.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 20))

        # Form
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=24)
        form.grid_columnconfigure(0, weight=1)

        # New password
        ctk.CTkLabel(
            form, text="New Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._pw_var = tk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self._pw_var,
            placeholder_text="Min 8 chars, 3 of: aA1!",
            height=38, show="*",
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        # Confirm password
        ctk.CTkLabel(
            form, text="Confirm Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self._confirm_var = tk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self._confirm_var,
            placeholder_text="Repeat password",
            height=38, show="*",
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=3, column=0, sticky="ew", pady=(0, 20))

        # Error label
        self._err_var = tk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._err_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=ACCENT_RED,
        ).grid(row=3, column=0, sticky="w", padx=24, pady=(0, 8))

        # Info box
        info_frame = ctk.CTkFrame(self, fg_color=BG_ELEVATED, corner_radius=8)
        info_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 20))
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            info_frame, text="ℹ️ Password Requirements",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=ACCENT_GOLD,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        ctk.CTkLabel(
            info_frame, text="• Minimum 8 characters\n"
                            "• At least 3 of: uppercase, lowercase, number, symbol",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 24))

        ctk.CTkButton(
            btn_frame, text="Reset Password",
            height=40, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white",
            command=self._submit,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Cancel",
            height=40, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self.destroy,
        ).pack(side="right")

    def _submit(self):
        """Submit password reset."""
        password = self._pw_var.get()
        confirm = self._confirm_var.get()

        # Validate
        if not password:
            self._err_var.set("Password is required.")
            return

        if password != confirm:
            self._err_var.set("Passwords do not match.")
            return

        # Validate strength
        from auth import validate_password_strength
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            self._err_var.set(msg)
            return

        # Reset password
        try:
            from auth import hash_password
            pwd_hash, salt = hash_password(password)
            self.db.update_user_password(self.username, pwd_hash, salt)
            
            # Log the action
            self.db.log_activity(
                "admin",  # Logged as admin action
                "PASSWORD_RESET",
                f"Reset password for user: {self.username}"
            )
            
            messagebox.showinfo(
                "Success",
                f"Password reset for {self.username}.\n\n"
                f"User should change it on next login."
            )
            
            if self.on_reset:
                self.on_reset()
            
            self.destroy()
        except Exception as e:
            self._err_var.set(f"Error: {str(e)}")
