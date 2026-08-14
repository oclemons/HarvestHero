"""user_management.py — Admin user management with create/edit/disable modals."""

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from auth import hash_password
from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_GOLD,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR,
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)
from toast import Toast


# ---------------------------------------------------------------------------
# Create / Edit User Modal
# ---------------------------------------------------------------------------

class _UserModal(ctk.CTkToplevel):
    """Modal for creating or editing a user."""

    def __init__(self, parent, db, current_admin: str,
                 user_data: dict = None, on_save=None):
        super().__init__(parent)
        self.db            = db
        self.current_admin = current_admin
        self.user_data     = user_data  # None = create mode
        self.on_save       = on_save
        self._edit_mode    = user_data is not None

        title = "Edit User" if self._edit_mode else "Create User"
        self.title(title)
        self.geometry("460x660")
        self.minsize(440, 620)
        self.resizable(False, False)
        # Defer build so the window frame is rendered before widgets are placed
        self.after(50, self._deferred_init)

    def _deferred_init(self):
        self.configure(fg_color=BG_SURFACE)
        self._build()
        self.update_idletasks()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Edit User" if self._edit_mode else "Create New User",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        ctk.CTkLabel(
            self,
            text="Edit account details below." if self._edit_mode
                 else "New users can log in immediately unless marked inactive.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=28)
        form.grid_columnconfigure(0, weight=1)

        def _field(label, var, row, placeholder="", show="", width=None):
            ctk.CTkLabel(
                form, text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_SECONDARY,
            ).grid(row=row * 2, column=0, sticky="w", pady=(10, 3))
            e = ctk.CTkEntry(
                form, textvariable=var,
                placeholder_text=placeholder,
                height=38, show=show,
                fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
                corner_radius=8,
            )
            e.grid(row=row * 2 + 1, column=0, sticky="ew")
            return e

        self._uv = tk.StringVar(value=self.user_data["username"] if self._edit_mode else "")
        self._fv = tk.StringVar(value=self.user_data.get("full_name", "") if self._edit_mode else "")
        self._pv = tk.StringVar()
        self._cv = tk.StringVar()
        self._rv = tk.StringVar(value=self.user_data["role"] if self._edit_mode else "staff")
        self._av = tk.BooleanVar(value=bool(self.user_data["is_active"]) if self._edit_mode else True)

        u_entry = _field("Username", self._uv, 0, "e.g. jdoe")
        if self._edit_mode:
            u_entry.configure(state="disabled")

        _field("Full Name  (optional)", self._fv, 1, "e.g. Jane Doe")

        if self._edit_mode:
            ctk.CTkLabel(
                form, text="New Password  (leave blank to keep current)",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_SECONDARY,
            ).grid(row=4, column=0, sticky="w", pady=(10, 3))
        else:
            ctk.CTkLabel(
                form, text="Password",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_SECONDARY,
            ).grid(row=4, column=0, sticky="w", pady=(10, 3))

        ctk.CTkEntry(
            form, textvariable=self._pv, placeholder_text="Min 8 chars, 3 of: aA1!",
            height=38, show="*",
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=5, column=0, sticky="ew")

        ctk.CTkLabel(
            form, text="Confirm Password",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=6, column=0, sticky="w", pady=(10, 3))
        ctk.CTkEntry(
            form, textvariable=self._cv, placeholder_text="Repeat password",
            height=38, show="*",
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=7, column=0, sticky="ew")

        ctk.CTkLabel(
            form, text="Role",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=8, column=0, sticky="w", pady=(10, 3))
        ctk.CTkOptionMenu(
            form, variable=self._rv, values=["staff", "admin"],
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, button_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
        ).grid(row=9, column=0, sticky="ew")

        ctk.CTkCheckBox(
            form, text="Account active  (uncheck to disable)",
            variable=self._av,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=BORDER_COLOR,
        ).grid(row=10, column=0, sticky="w", pady=(14, 0))

        # Error label
        self._err_var = tk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._err_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=ACCENT_RED,
        ).grid(row=3, column=0, sticky="w", padx=28, pady=(8, 0))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=28, pady=(20, 24))
        ctk.CTkButton(
            btn_row, text="Save" if self._edit_mode else "Create User",
            height=42, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._submit,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Cancel",
            height=42, corner_radius=10,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self.destroy,
        ).pack(side="left")

    def _submit(self):
        username  = self._uv.get().strip()
        full_name = self._fv.get().strip()
        password  = self._pv.get()
        confirm   = self._cv.get()
        role      = self._rv.get()
        active    = self._av.get()

        # Validate
        if not self._edit_mode and not username:
            self._err_var.set("Username is required.")
            return
        if not self._edit_mode and not password:
            self._err_var.set("Password is required.")
            return
        if password:
            from auth import validate_password_strength
            ok, msg = validate_password_strength(password)
            if not ok:
                self._err_var.set(msg)
                return
        if password and password != confirm:
            self._err_var.set("Passwords do not match.")
            return
        if not role:
            self._err_var.set("Role is required.")
            return

        if self._edit_mode:
            uid = self.user_data["id"]
            if password:
                ph, salt = hash_password(password)
                self.db.update_user_password(uid, ph, salt)
            self.db.update_user_role(uid, role)
            self.db.update_user_full_name(uid, full_name)
            self.db.set_user_active(uid, active)
            if self.on_save:
                self.on_save("edited", username)
            self.destroy()
        else:
            ph, salt = hash_password(password)
            ok, msg = self.db.create_user_full(
                username, ph, salt, role, full_name,
                created_by=self.current_admin,
            )
            if ok:
                self.db.set_user_active(
                    self._get_new_uid(username), active)
                if self.on_save:
                    self.on_save("created", username)
                self.destroy()
            else:
                self._err_var.set(msg)

    def _get_new_uid(self, username: str) -> int:
        for u in self.db.get_all_users():
            if u["username"] == username:
                return u["id"]
        return -1


# ---------------------------------------------------------------------------
# Main UserManagement frame
# ---------------------------------------------------------------------------

class UserManagement(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict = None, embedded=False):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db        = db
        self.user      = user or {}
        self._is_admin = self.user.get("role") == "admin"
        self._build()
        self._load()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=40, pady=(28, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="Users",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        if self._is_admin:
            ctk.CTkButton(
                hdr, text="+ Create User", height=38, corner_radius=10,
                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                text_color="white",
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                command=self._open_create,
            ).grid(row=0, column=2, sticky="e")

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.grid(row=1, column=0, sticky="ew", padx=40, pady=(16, 0))
        self._tab_btns: dict = {}
        self._active_tab = tk.StringVar(value="users")

        for key, label in [("users", "Accounts"), ("activity", "Activity Log")]:
            b = ctk.CTkButton(
                tab_bar, text=label, width=130, height=34, corner_radius=8,
                fg_color=BG_ELEVATED if key == "users" else "transparent",
                hover_color=BG_ELEVATED,
                text_color=TEXT_PRIMARY if key == "users" else TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=lambda k=key: self._switch_tab(k),
            )
            b.pack(side="left", padx=(0, 4))
            self._tab_btns[key] = b

        # Panels
        self._users_panel = self._build_users_panel()
        self._users_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=8)

        self._activity_panel = self._build_activity_panel()
        self._activity_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=8)
        self._activity_panel.grid_remove()

    def _build_users_panel(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Treeview card
        card = ctk.CTkFrame(
            panel, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=40, pady=(0, 4))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("UM.Treeview",
                rowheight=32, font=(FONT_FAMILY, 10),
                background=BG_ELEVATED, fieldbackground=BG_ELEVATED,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("UM.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_ELEVATED, foreground=ACCENT_GOLD,
                relief="flat", padding=8)
            style.map("UM.Treeview",
                background=[("selected", ACCENT)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        cols = ("username", "full_name", "role", "status", "created_at", "last_login", "created_by")
        self.tree = ttk.Treeview(
            card, columns=cols, show="headings",
            selectmode="browse", style="UM.Treeview")
        for col, heading, width in [
            ("username",   "Username",    140),
            ("full_name",  "Full Name",   160),
            ("role",       "Role",         90),
            ("status",     "Status",       80),
            ("created_at", "Created",     150),
            ("last_login", "Last Login",  150),
            ("created_by", "Created By",  120),
        ]:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=40)

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("active",   background=BG_ELEVATED, foreground=TEXT_PRIMARY)
        self.tree.tag_configure("inactive", background=BG_OVERLAY,  foreground=TEXT_MUTED)
        self.tree.tag_configure("admin",    foreground=ACCENT_GOLD)

        # Action row
        if self._is_admin:
            acts = ctk.CTkFrame(panel, fg_color="transparent")
            acts.grid(row=1, column=0, padx=40, pady=(4, 12), sticky="w")

            for label, color, cmd in [
                ("Edit",             BG_ELEVATED,  self._edit_user),
                ("Reset Password",   ACCENT_AMBER, self._reset_password),
                ("Enable / Disable", BG_ELEVATED,  self._toggle_active),
                ("Archive",          ACCENT_RED,   self._delete_user),
            ]:
                ctk.CTkButton(
                    acts, text=label, height=34, corner_radius=8,
                    fg_color=color, hover_color=BG_HOVER if color == BG_ELEVATED else color,
                    text_color=TEXT_SECONDARY if color == BG_ELEVATED else "white",
                    border_width=1, border_color=BORDER_COLOR,
                    command=cmd,
                ).pack(side="left", padx=(0, 8))

        return panel

    def _build_activity_panel(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Toolbar — retention note + admin-only "Clear History"
        toolbar = ctk.CTkFrame(panel, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=40, pady=(0, 8))
        toolbar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            toolbar,
            text="Entries older than 30 days are removed automatically.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, sticky="w")

        if self._is_admin:
            ctk.CTkButton(
                toolbar, text="Clear History", height=32, width=130,
                corner_radius=8, fg_color=BG_OVERLAY, hover_color=ACCENT_RED,
                text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                command=self._confirm_clear_activity,
            ).grid(row=0, column=1, sticky="e")

        card = ctk.CTkFrame(
            panel, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=1, column=0, sticky="nsew", padx=40, pady=(0, 12))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("Act2.Treeview",
                rowheight=28, font=(FONT_FAMILY, 10),
                background=BG_ELEVATED, fieldbackground=BG_ELEVATED,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Act2.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_ELEVATED, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Act2.Treeview",
                background=[("selected", ACCENT)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        acols = ("timestamp", "username", "action", "detail")
        self.act_tree = ttk.Treeview(
            card, columns=acols, show="headings", style="Act2.Treeview")
        for col, heading, width in [
            ("timestamp", "Timestamp", 160),
            ("username",  "User",      130),
            ("action",    "Action",    120),
            ("detail",    "Detail",    400),
        ]:
            self.act_tree.heading(col, text=heading)
            self.act_tree.column(col, width=width, minwidth=40)

        self.act_tree.tag_configure("LOGIN",    foreground="#93c5fd")
        self.act_tree.tag_configure("SCAN_IN",  foreground="#86efac")
        self.act_tree.tag_configure("SCAN_OUT", foreground="#fca5a5")

        avsb = ttk.Scrollbar(card, orient="vertical", command=self.act_tree.yview)
        self.act_tree.configure(yscrollcommand=avsb.set)
        self.act_tree.grid(row=0, column=0, sticky="nsew")
        avsb.grid(row=0, column=1, sticky="ns")

        return panel

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _switch_tab(self, key: str):
        self._active_tab.set(key)
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.configure(fg_color=BG_ELEVATED, text_color=TEXT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)
        if key == "users":
            self._activity_panel.grid_remove()
            self._users_panel.grid()
        else:
            self._users_panel.grid_remove()
            self._activity_panel.grid()
            self._load_activity()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def on_shown(self):
        self._load()

    def _load(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for u in self.db.get_all_users():
            status = "Active" if u["is_active"] else "Disabled"
            tags = []
            if not u["is_active"]:
                tags.append("inactive")
            elif u["role"] == "admin":
                tags.append("admin")
            else:
                tags.append("active")
            self.tree.insert(
                "", "end", iid=str(u["id"]),
                tags=tags,
                values=(
                    u["username"],
                    u.get("full_name") or "",
                    u["role"],
                    status,
                    u.get("created_at") or "",
                    u.get("last_login") or "Never",
                    u.get("created_by") or "",
                ),
            )

    def _load_activity(self):
        for r in self.act_tree.get_children():
            self.act_tree.delete(r)
        for row in self.db.get_activity_log():
            action = row["action"]
            tag = "LOGIN" if action == "LOGIN" else (
                  "SCAN_IN" if "SCAN_IN" in action else (
                  "SCAN_OUT" if "SCAN_OUT" in action else ""))
            self.act_tree.insert("", "end", tags=(tag,), values=(
                row["timestamp"], row["username"],
                row["action"], row["detail"]))

    def _confirm_clear_activity(self):
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Clear Activity History",
            "This will permanently delete all activity log entries.\n\n"
            "This action cannot be undone. Continue?",
            icon="warning",
        ):
            return
        deleted = self.db.clear_activity_log()
        self._load_activity()
        Toast.show(self, f"Cleared {deleted} activity log entr"
                          f"{'y' if deleted == 1 else 'ies'}", kind="success")

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------

    def _selected_user(self):
        sel = self.tree.selection()
        if not sel:
            Toast.show(self, "Select a user first", kind="warning")
            return None
        uid = int(sel[0])
        for u in self.db.get_all_users():
            if u["id"] == uid:
                return u
        return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_create(self):
        _UserModal(
            self.winfo_toplevel(), self.db,
            current_admin=self.user.get("username", ""),
            on_save=self._on_modal_save,
        )

    def _edit_user(self):
        u = self._selected_user()
        if not u:
            return
        _UserModal(
            self.winfo_toplevel(), self.db,
            current_admin=self.user.get("username", ""),
            user_data=u,
            on_save=self._on_modal_save,
        )

    def _on_modal_save(self, action: str, username: str):
        self._load()
        if action == "created":
            Toast.show(
                self,
                f"User '{username}' created. They can now log in.",
                kind="success",
            )
        else:
            Toast.show(self, f"User '{username}' updated.", kind="success")

    def _toggle_active(self):
        u = self._selected_user()
        if not u:
            return
        if u["username"] == self.user.get("username"):
            Toast.show(self, "You cannot disable your own account", kind="warning")
            return
        new_state = not bool(u["is_active"])
        self.db.set_user_active(u["id"], new_state)
        self._load()
        state_str = "enabled" if new_state else "disabled"
        Toast.show(self, f"'{u['username']}' has been {state_str}.", kind="success")

    def _reset_password(self):
        u = self._selected_user()
        if not u:
            return
        # Use the new password reset dialog
        from password_reset_dialog import AdminPasswordResetDialog
        dlg = AdminPasswordResetDialog(
            self.winfo_toplevel(),
            self.db,
            u["username"],
            on_reset=self._load
        )
        dlg.wait_window()
        # Reload after reset
        self._load()

    def _delete_user(self):
        u = self._selected_user()
        if not u:
            return
        if u["username"] == self.user.get("username"):
            Toast.show(self, "You cannot archive your own account", kind="warning")
            return
        from tkinter import messagebox
        if messagebox.askyesno(
            "Confirm Archive",
            f"Archive '{u['username']}'?\n\nThey will be removed from active users "
            "and can be restored later from the Archive Manager.",
        ):
            self.db.archive_user(u["id"], archived_by=self.user.get("username", ""))
            self._load()
            Toast.show(self, f"User '{u['username']}' archived.", kind="success")
