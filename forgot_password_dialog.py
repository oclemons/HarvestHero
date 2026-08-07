"""forgot_password_dialog.py — Admin-authorized password reset dialog."""

import tkinter as tk

import customtkinter as ctk

from auth import hash_password, verify_password
from theme import (
    BG_CARD, BG_SECONDARY, BG_HOVER,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)


class ForgotPasswordDialog(ctk.CTkToplevel):
    """
    Password reset flow that requires an admin to authorize the change.

    Steps:
      1. Enter the account username to reset.
      2. Enter new password + confirm.
      3. Provide any active admin's username + password to authorize.
    """

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Reset Password")
        self.geometry("460x540")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG_CARD)
        self._build()
        self.after(100, self.lift)

    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.grid(row=0, column=0, padx=40, pady=30, sticky="nsew")
        inner.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            inner, text="Reset Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            inner,
            text="An admin must authorize this reset.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 20))

        # ── Section 1: Account to reset ──────────────────────────────
        self._section_label(inner, "ACCOUNT TO RESET", row=2)
        self.account_var = tk.StringVar()
        ctk.CTkEntry(
            inner, textvariable=self.account_var,
            placeholder_text="Username of account to reset",
            height=42, fg_color=BG_SECONDARY,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=8,
        ).grid(row=3, column=0, sticky="ew", pady=(4, 16))

        # ── Section 2: New password ───────────────────────────────────
        self._section_label(inner, "NEW PASSWORD", row=4)
        self.new_pass_var = tk.StringVar()
        ctk.CTkEntry(
            inner, textvariable=self.new_pass_var,
            placeholder_text="New password (min 8 chars, 3 of: aA1!)",
            show="●", height=42, fg_color=BG_SECONDARY,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=8,
        ).grid(row=5, column=0, sticky="ew", pady=(4, 8))

        self.confirm_var = tk.StringVar()
        ctk.CTkEntry(
            inner, textvariable=self.confirm_var,
            placeholder_text="Confirm new password",
            show="●", height=42, fg_color=BG_SECONDARY,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=8,
        ).grid(row=6, column=0, sticky="ew", pady=(0, 16))

        # ── Section 3: Admin authorization ───────────────────────────
        self._section_label(inner, "ADMIN AUTHORIZATION", row=7)

        self.admin_user_var = tk.StringVar()
        ctk.CTkEntry(
            inner, textvariable=self.admin_user_var,
            placeholder_text="Admin username",
            height=42, fg_color=BG_SECONDARY,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=8,
        ).grid(row=8, column=0, sticky="ew", pady=(4, 8))

        self.admin_pass_var = tk.StringVar()
        ctk.CTkEntry(
            inner, textvariable=self.admin_pass_var,
            placeholder_text="Admin password",
            show="●", height=42, fg_color=BG_SECONDARY,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=8,
        ).grid(row=9, column=0, sticky="ew", pady=(0, 8))

        # Status label
        self._status_lbl = ctk.CTkLabel(
            inner, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=ACCENT_RED, height=20, anchor="w",
        )
        self._status_lbl.grid(row=10, column=0, sticky="w", pady=(0, 12))

        # Buttons
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.grid(row=11, column=0, sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row, text="Reset Password",
            height=46, corner_radius=8,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
            text_color="#1B1F24",
            command=self._submit,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Cancel",
            height=46, corner_radius=8, width=90,
            fg_color=BG_SECONDARY, hover_color=BG_HOVER,
            text_color=TEXT_MUTED,
            command=self.destroy,
        ).grid(row=0, column=1)

    # ------------------------------------------------------------------

    def _section_label(self, parent, text: str, row: int):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=row, column=0, sticky="w")

    def _set_status(self, msg: str, color=None):
        self._status_lbl.configure(
            text=msg,
            text_color=color or ACCENT_RED,
        )

    # ------------------------------------------------------------------

    def _submit(self):
        account  = self.account_var.get().strip()
        new_pass = self.new_pass_var.get()
        confirm  = self.confirm_var.get()
        adm_user = self.admin_user_var.get().strip()
        adm_pass = self.admin_pass_var.get()

        # Basic validation
        if not all([account, new_pass, confirm, adm_user, adm_pass]):
            self._set_status("All fields are required.")
            return

        if new_pass != confirm:
            self._set_status("New passwords do not match.")
            return

        from auth import validate_password_strength
        ok, msg = validate_password_strength(new_pass)
        if not ok:
            self._set_status(msg)
            return

        # Verify admin credentials
        admin_rec = self.db.get_user(adm_user)
        if (not admin_rec
                or admin_rec.get("role") != "admin"
                or not admin_rec.get("is_active")
                or not verify_password(adm_pass,
                                       admin_rec["password_hash"],
                                       admin_rec["salt"])):
            self._set_status("Admin credentials are incorrect or account is not active.")
            return

        # Verify target account exists
        target = self.db.get_user(account)
        if not target:
            self._set_status(f"Account '{account}' does not exist.")
            return

        # Perform reset
        pwd_hash, salt = hash_password(new_pass)
        self.db.update_user_password(target["id"], pwd_hash, salt)

        self._set_status(
            f"✓  Password for '{account}' has been reset successfully.",
            color=ACCENT_GREEN,
        )
        # Auto-close after 2 seconds
        self.after(2000, self.destroy)
