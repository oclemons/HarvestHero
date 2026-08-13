"""env_dashboard.py — Admin Environment & License management page."""

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from environment import load_license, write_license, get_client_info, _machine_id
from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GOLD,
    SECONDARY_ACCENT, SECONDARY_ACCENT_HOVER,
    ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
    BG_PRIMARY, BG_CARD,
)
from toast import Toast


class EnvDashboard(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db   = db
        self.user = user
        self._build()

    # ------------------------------------------------------------------

    def _section(self, scroll, title: str, subtitle: str, row: int):
        f = ctk.CTkFrame(scroll, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew", padx=40, pady=(24, 6))
        ctk.CTkLabel(
            f, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                f, text=subtitle,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED,
            ).pack(anchor="w")

    def _card(self, scroll, row: int) -> ctk.CTkFrame:
        f = ctk.CTkFrame(
            scroll, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        f.grid(row=row, column=0, sticky="ew", padx=40)
        f.grid_columnconfigure(1, weight=1)
        return f

    def _info_row(self, card, label: str, value: str, row: int,
                  color: str = None):
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=row, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=color or TEXT_PRIMARY, anchor="e",
        ).grid(row=row, column=1, padx=(0, 20), pady=10, sticky="e")

    def _divider(self, card, row: int):
        ctk.CTkFrame(card, height=1, fg_color=BORDER_COLOR).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=20)

    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=40, pady=(28, 0))
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            hdr, text="Environment",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            hdr, text="Refresh", width=90, height=32,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=8,
            border_width=1, border_color=BORDER_COLOR,
            command=self.on_shown,
        ).grid(row=0, column=2, sticky="e")

        r = 1

        # ── License Info ────────────────────────────────────────────
        self._section(scroll, "License & Organization",
                      "Current environment authorization.", r)
        r += 1
        self._lic_card = self._card(scroll, r); r += 1
        self._populate_license(self._lic_card)

        # ── Host Machine ────────────────────────────────────────────
        self._section(scroll, "This Machine",
                      "Machine identity for this installation.", r)
        r += 1
        host_card = self._card(scroll, r); r += 1
        info = get_client_info()
        self._info_row(host_card, "Hostname",   info["hostname"],   0)
        self._divider(host_card, 1)
        self._info_row(host_card, "IP Address", info["ip"],         2)
        self._divider(host_card, 3)
        self._info_row(host_card, "Machine ID", info["machine_id"][:16] + "…", 4,
                       TEXT_MUTED)

        # ── Registered Clients ──────────────────────────────────────
        self._section(scroll, "Registered Clients",
                      "Computers that have connected to this host.", r)
        r += 1
        clients_card = ctk.CTkFrame(
            scroll, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        clients_card.grid(row=r, column=0, sticky="ew", padx=40)
        clients_card.grid_columnconfigure(0, weight=1)
        r += 1

        try:
            style = ttk.Style()
            style.configure("Env.Treeview",
                rowheight=30, font=(FONT_FAMILY, 10),
                background=BG_ELEVATED, fieldbackground=BG_ELEVATED,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Env.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_ELEVATED, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Env.Treeview",
                background=[("selected", ACCENT)],
                foreground=[("selected", BG_BASE)])
        except Exception:
            pass

        cols = ("hostname", "ip", "status", "registered", "last_seen", "approved_by")
        self._client_tree = ttk.Treeview(
            clients_card, columns=cols, show="headings",
            style="Env.Treeview", height=6)
        for col, heading, width in [
            ("hostname",    "Hostname",     160),
            ("ip",          "IP Address",   130),
            ("status",      "Status",        90),
            ("registered",  "Registered",   150),
            ("last_seen",   "Last Seen",    150),
            ("approved_by", "Approved By",  130),
        ]:
            self._client_tree.heading(col, text=heading)
            self._client_tree.column(col, width=width, minwidth=40)

        self._client_tree.tag_configure("approved",  foreground="#86efac")
        self._client_tree.tag_configure("pending",   foreground=ACCENT_AMBER)

        vsb = ttk.Scrollbar(
            clients_card, orient="vertical", command=self._client_tree.yview)
        self._client_tree.configure(yscrollcommand=vsb.set)
        self._client_tree.grid(row=0, column=0, sticky="ew", padx=0)
        vsb.grid(row=0, column=1, sticky="ns")

        # Action buttons
        act = ctk.CTkFrame(clients_card, fg_color="transparent")
        act.grid(row=1, column=0, columnspan=2, padx=20, pady=12, sticky="w")
        ctk.CTkButton(
            act, text="Approve Selected", height=36, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#3A6648",
            text_color="white",
            command=self._approve_client,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            act, text="Revoke Selected", height=36, corner_radius=8,
            fg_color=ACCENT_RED, hover_color="#6B2A2A",
            text_color="white",
            command=self._revoke_client,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            act, text="Register This Machine", height=36, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self._register_self,
        ).pack(side="left")

        self._populate_clients()

        # ── Data Management ──────────────────────────────────────────
        self._section(scroll, "Data Management",
                      "Clear historical data (admin only).", r)
        r += 1
        dm = self._card(scroll, r); r += 1
        
        ctk.CTkLabel(
            dm, text="Clear Transaction History",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(16, 4))
        
        ctk.CTkLabel(
            dm, text="Permanently delete all inventory transaction records. This cannot be undone.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(0, 12))
        
        btn_row = ctk.CTkFrame(dm, fg_color="transparent")
        btn_row.pack(anchor="w", padx=20, pady=(0, 16))
        ctk.CTkButton(
            btn_row, text="🗑 Clear All Transactions",
            height=38, corner_radius=8,
            fg_color=ACCENT_RED, hover_color="#dc2626",
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._clear_transactions,
        ).pack(side="left", padx=(0, 10))

        # ── License Management ──────────────────────────────────────
        self._section(scroll, "License Management",
                      "Update organization name or regenerate environment ID.", r)
        r += 1
        lm = self._card(scroll, r); r += 1
        lm.grid_columnconfigure(1, weight=1)

        self._org_var = tk.StringVar()
        ctk.CTkLabel(
            lm, text="Organization Name",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=0, column=0, padx=20, pady=12, sticky="w")
        ctk.CTkEntry(
            lm, textvariable=self._org_var,
            placeholder_text="Organization name",
            height=38, fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=0, column=1, padx=(0, 20), pady=12, sticky="ew")

        lic = load_license()
        if lic:
            self._org_var.set(lic.get("org_name", ""))

        btn_row = ctk.CTkFrame(lm, fg_color="transparent")
        btn_row.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="w")
        ctk.CTkButton(
            btn_row, text="Save License",
            height=38, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_BASE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._save_license,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Regenerate Environment ID",
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self._regen_env_id,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def _populate_license(self, card):
        for w in card.winfo_children():
            w.destroy()
        card.grid_columnconfigure(1, weight=1)

        lic = load_license()
        if not lic:
            ctk.CTkLabel(
                card, text="No license file found. Running in unregistered mode.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=ACCENT_AMBER,
            ).grid(row=0, column=0, columnspan=2, padx=20, pady=16, sticky="w")
            return

        rows = [
            ("Organization",  lic.get("org_name", "—"),       None),
            ("Environment ID", lic.get("environment_id", "—"), ACCENT),
            ("Host Machine ID", lic.get("host_machine_id", "—")[:16] + "…", TEXT_MUTED),
            ("Created",       lic.get("created_at", "—")[:10], None),
            ("Expiry",        lic.get("expiry") or "Never",
             ACCENT_RED if lic.get("expiry") else ACCENT_GREEN),
        ]
        for i, (label, val, color) in enumerate(rows):
            self._info_row(card, label, val, i * 2, color)
            if i < len(rows) - 1:
                self._divider(card, i * 2 + 1)

    def _populate_clients(self):
        for r in self._client_tree.get_children():
            self._client_tree.delete(r)
        for c in self.db.get_all_clients():
            status = "Approved" if c["is_approved"] else "Pending"
            tag    = "approved" if c["is_approved"] else "pending"
            self._client_tree.insert(
                "", "end",
                iid=c["machine_id"],
                tags=(tag,),
                values=(
                    c["hostname"],
                    c["ip_address"],
                    status,
                    c["registered_at"],
                    c["last_seen"] or "—",
                    c["approved_by"] or "—",
                ),
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _approve_client(self):
        sel = self._client_tree.selection()
        if not sel:
            Toast.show(self, "Select a client first", kind="warning")
            return
        mid = sel[0]
        self.db.set_client_approved(mid, True, self.user.get("username", ""))
        self._populate_clients()
        Toast.show(self, "Client approved", kind="success")

    def _revoke_client(self):
        sel = self._client_tree.selection()
        if not sel:
            Toast.show(self, "Select a client first", kind="warning")
            return
        mid = sel[0]
        self.db.set_client_approved(mid, False)
        self._populate_clients()
        Toast.show(self, "Client access revoked", kind="success")

    def _register_self(self):
        info = get_client_info()
        is_new = self.db.upsert_client(
            info["machine_id"], info["hostname"], info["ip"])
        if is_new:
            self.db.set_client_approved(
                info["machine_id"], True, "auto-registered")
        self._populate_clients()
        Toast.show(self, "This machine is registered", kind="success")

    def _save_license(self):
        org = self._org_var.get().strip()
        if not org:
            Toast.show(self, "Organization name required", kind="warning")
            return
        lic = load_license()
        env_id = lic["environment_id"] if lic else "NEW"
        write_license(org, env_id)
        self._populate_license(self._lic_card)
        Toast.show(self, "License saved", kind="success")

    def _regen_env_id(self):
        import uuid
        org = self._org_var.get().strip() or "Inventory Control Center"
        new_id = str(uuid.uuid4())[:8].upper()
        write_license(org, new_id)
        self._populate_license(self._lic_card)
        Toast.show(self, f"New environment ID: {new_id}", kind="info")

    def _clear_transactions(self):
        """Clear all transaction history (admin only)."""
        from tkinter import messagebox
        
        if not messagebox.askyesno(
            "Confirm Clear Transactions",
            "Delete ALL transaction history?\n\n"
            "This action cannot be undone. All inventory transaction records will be permanently deleted.",
            icon="warning",
        ):
            return
        
        try:
            # Delete all transactions
            conn = self.db._connect()
            conn.execute("DELETE FROM transactions")
            conn.commit()
            conn.close()
            
            Toast.show(self, "✓ All transaction history cleared", kind="success")
            self.db.log_activity(
                self.user.get("username", ""),
                "CLEAR_TRANSACTIONS",
                "Cleared all transaction history"
            )
        except Exception as e:
            Toast.show(self, f"Error clearing transactions: {str(e)}", kind="error")

    def on_shown(self):
        self._populate_license(self._lic_card)
        self._populate_clients()
