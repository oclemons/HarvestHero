"""admin_password_reset_dialog.py — Email-based password reset for admins.

Allows admins to reset their own password via email.
Uses secure token-based reset system.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from theme import (
    BG_PRIMARY, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)
from email_service import get_email_service


class AdminPasswordResetDialog(ctk.CTkToplevel):
    """Dialog for admin to reset their own password via email."""

    def __init__(self, parent, db, admin_username: str, admin_email: str):
        super().__init__(parent)
        self.db = db
        self.admin_username = admin_username
        self.admin_email = admin_email
        self.email_service = get_email_service()
        self.reset_token = None
        
        self.title("Reset Your Password")
        self.geometry("550x650")
        self.resizable(False, False)
        self.grab_set()
        
        self._current_step = 1  # Step 1: Request, Step 2: Enter token, Step 3: Set password
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the dialog."""
        self.configure(fg_color=BG_SURFACE)
        self.grid_columnconfigure(0, weight=1)
        
        # Main frame
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        main.grid_columnconfigure(0, weight=1)
        
        # Title
        ctk.CTkLabel(
            main, text="🔐 Reset Your Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        # Description
        ctk.CTkLabel(
            main, text="For security, password resets require email verification.\n"
                      "A reset token will be sent to your email address.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 20))
        
        # Content frame (will be updated based on step)
        self.content_frame = ctk.CTkFrame(main, fg_color="transparent")
        self.content_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # Error label
        self._err_var = tk.StringVar()
        ctk.CTkLabel(
            main, textvariable=self._err_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=ACCENT_RED,
        ).grid(row=3, column=0, sticky="w", pady=(0, 8))
        
        # Button frame
        self.btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, sticky="ew")
        
        self._show_step_1()

    def _show_step_1(self):
        """Show step 1: Request reset token."""
        self._current_step = 1
        self._clear_content()
        
        # Email configuration check
        if not self.email_service.is_configured():
            ctk.CTkLabel(
                self.content_frame, text="⚠️ Email Service Not Configured",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=ACCENT_RED,
            ).pack(anchor="w", pady=(0, 10))
            
            ctk.CTkLabel(
                self.content_frame, 
                text="The email service has not been configured yet.\n"
                     "Contact your system administrator to set up email.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_SECONDARY,
                justify="left",
            ).pack(anchor="w", pady=(0, 20))
            
            self._clear_buttons()
            ctk.CTkButton(
                self.btn_frame, text="Close",
                height=40, corner_radius=8,
                fg_color=BG_ELEVATED, hover_color=BG_HOVER,
                text_color=TEXT_SECONDARY,
                border_width=1, border_color=BORDER_COLOR,
                command=self.destroy,
            ).pack(side="right")
            return
        
        # Info box
        info_frame = ctk.CTkFrame(self.content_frame, fg_color=BG_ELEVATED, corner_radius=8)
        info_frame.pack(fill="x", pady=(0, 20))
        info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            info_frame, text="📧 Email Verification",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=ACCENT_GOLD,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))
        
        ctk.CTkLabel(
            info_frame, 
            text=f"A reset token will be sent to:\n{self.admin_email}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 12))
        
        # Buttons
        self._clear_buttons()
        ctk.CTkButton(
            self.btn_frame, text="Send Reset Token",
            height=40, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white",
            command=self._send_reset_token,
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            self.btn_frame, text="Cancel",
            height=40, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self.destroy,
        ).pack(side="right")

    def _show_step_2(self):
        """Show step 2: Enter reset token."""
        self._current_step = 2
        self._clear_content()
        
        ctk.CTkLabel(
            self.content_frame, text="Reset Token",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        
        self._token_var = tk.StringVar()
        ctk.CTkEntry(
            self.content_frame, textvariable=self._token_var,
            placeholder_text="Paste the token from your email",
            height=38,
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(fill="x", pady=(0, 20))
        
        # Buttons
        self._clear_buttons()
        ctk.CTkButton(
            self.btn_frame, text="Verify Token",
            height=40, corner_radius=8,
            fg_color=ACCENT, hover_color="#1d4ed8",
            text_color="white",
            command=self._verify_token,
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            self.btn_frame, text="Back",
            height=40, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self._show_step_1,
        ).pack(side="right")

    def _show_step_3(self):
        """Show step 3: Set new password."""
        self._current_step = 3
        self._clear_content()
        
        ctk.CTkLabel(
            self.content_frame, text="New Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        
        self._pw_var = tk.StringVar()
        ctk.CTkEntry(
            self.content_frame, textvariable=self._pw_var,
            placeholder_text="Min 8 chars, 3 of: aA1!",
            height=38, show="*",
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(
            self.content_frame, text="Confirm Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        
        self._confirm_var = tk.StringVar()
        ctk.CTkEntry(
            self.content_frame, textvariable=self._confirm_var,
            placeholder_text="Repeat password",
            height=38, show="*",
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(fill="x", pady=(0, 20))
        
        # Buttons
        self._clear_buttons()
        ctk.CTkButton(
            self.btn_frame, text="Reset Password",
            height=40, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white",
            command=self._reset_password,
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            self.btn_frame, text="Back",
            height=40, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self._show_step_2,
        ).pack(side="right")

    def _clear_content(self):
        """Clear content frame."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _clear_buttons(self):
        """Clear button frame."""
        for widget in self.btn_frame.winfo_children():
            widget.destroy()

    def _send_reset_token(self):
        """Send reset token to admin email."""
        try:
            # Generate token
            self.reset_token = self.email_service.generate_reset_token(self.admin_username)
            
            # Send email
            success, message = self.email_service.send_password_reset_email(
                self.admin_email,
                self.admin_username,
                self.reset_token,
                "Admin"
            )
            
            if success:
                self._show_step_2()
            else:
                self._err_var.set(message)
        except Exception as e:
            self._err_var.set(f"Error: {str(e)}")

    def _verify_token(self):
        """Verify the reset token."""
        token = self._token_var.get().strip()
        
        if not token:
            self._err_var.set("Please enter the reset token from your email.")
            return
        
        is_valid, result = self.email_service.validate_reset_token(token)
        
        if is_valid:
            self.reset_token = token
            self._show_step_3()
        else:
            self._err_var.set(result)

    def _reset_password(self):
        """Reset the password."""
        password = self._pw_var.get()
        confirm = self._confirm_var.get()
        
        if not password:
            self._err_var.set("Password is required.")
            return
        
        if password != confirm:
            self._err_var.set("Passwords do not match.")
            return
        
        # Validate strength
        from auth import validate_password_strength, hash_password
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            self._err_var.set(msg)
            return
        
        try:
            # Update password
            pwd_hash, salt = hash_password(password)
            self.db.update_user_password(self.admin_username, pwd_hash, salt)
            
            # Mark token as used
            self.email_service.mark_token_used(self.reset_token)
            
            # Log the action
            self.db.log_activity(
                self.admin_username,
                "PASSWORD_RESET",
                "Admin reset own password via email"
            )
            
            messagebox.showinfo(
                "Success",
                "Your password has been reset successfully.\n\n"
                "Please log in with your new password."
            )
            
            self.destroy()
        except Exception as e:
            self._err_var.set(f"Error: {str(e)}")
