"""archive_manager.py — View, restore, and permanently delete archived records."""

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR,
)
from toast import Toast


def _apply_treeview_style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Treeview",
                    rowheight=30, font=(FONT_FAMILY, 10),
                    background=BG_SECONDARY, fieldbackground=BG_SECONDARY,
                    foreground=TEXT_PRIMARY, borderwidth=0)
    style.configure("Treeview.Heading",
                    font=(FONT_FAMILY, 10, "bold"),
                    background=BG_CARD, foreground=ACCENT_GOLD,
                    relief="flat", padding=6)
    style.map("Treeview",
              background=[("selected", ACCENT_BLUE)],
              foreground=[("selected", "white")])


class _BaseArchiveTab(ctk.CTkFrame):
    """Reusable archive viewer tab."""

    _kind = "record"
    _name_key = "name"
    _columns = []
    _headers = []
    _widths = []

    def __init__(self, parent, db, user: dict, on_update=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self.user = user
        self.on_update = on_update
        self._tree = None
        self._count_lbl = None
        self._search_var = tk.StringVar()
        self._build()
        self.load()

    # Override in subclasses
    def _fetch(self, search: str):
        return []

    def _restore(self, archive_id: int) -> bool:
        return False

    def _delete(self, archive_id: int) -> bool:
        return False

    def _row_values(self, record) -> tuple:
        return tuple(record.get(c, "") for c in self._columns)

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 8))

        ctk.CTkEntry(
            top, textvariable=self._search_var, width=240, height=36,
            placeholder_text=f"Search archived {self._kind}…",
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            top, text="↻ Refresh", width=80, height=36,
            fg_color=BG_SECONDARY, hover_color=BG_CARD,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self.load,
        ).pack(side="left", padx=4)

        if self.user["role"] == "admin":
            ctk.CTkButton(
                top, text="Restore", width=80, height=36,
                fg_color=ACCENT_GREEN, hover_color="#15803d",
                text_color="white", corner_radius=8,
                command=self._restore_selected,
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                top, text="Delete", width=80, height=36,
                fg_color=ACCENT_RED, hover_color="#b91c1c",
                text_color="white", corner_radius=8,
                command=self._permanently_delete_selected,
            ).pack(side="right", padx=4)

        tree_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(tree_frame, columns=self._columns,
                                  show="headings", selectmode="browse")
        for i, col in enumerate(self._columns):
            self._tree.heading(col, text=self._headers[i])
            self._tree.column(col, width=self._widths[i], minwidth=50)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._count_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self._count_lbl.grid(row=2, column=0, pady=(0, 10))

        self._search_var.trace_add("write", lambda *_: self.load())

    def load(self):
        search = self._search_var.get().strip()
        records = self._fetch(search)

        for r in self._tree.get_children():
            self._tree.delete(r)

        for rec in records:
            self._tree.insert("", "end", iid=str(rec["archive_id"]),
                              values=self._row_values(rec))

        self._count_lbl.configure(text=f"{len(records)} archived {self._kind}(s)")

    def _selected(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", f"Please select an archived {self._kind} first.")
            return None
        archive_id = int(sel[0])
        for rec in self._fetch():
            if rec["archive_id"] == archive_id:
                return rec
        return None

    def _restore_selected(self):
        rec = self._selected()
        if not rec:
            return
        name = rec.get(self._name_key, "record")
        if messagebox.askyesno("Confirm Restore", f"Restore '{name}'?"):
            if self._restore(rec["archive_id"]):
                Toast.show(self, f"'{name}' restored", kind="success")
                self.load()
                if self.on_update:
                    self.on_update()
            else:
                Toast.show(self, "Restore failed", kind="error")

    def _permanently_delete_selected(self):
        rec = self._selected()
        if not rec:
            return
        name = rec.get(self._name_key, "record")
        if messagebox.askyesno(
            "Confirm Permanent Delete",
            f"Permanently delete archived '{name}'?\n\nThis cannot be undone.",
            icon="warning",
        ):
            if self._delete(rec["archive_id"]):
                Toast.show(self, f"'{name}' permanently deleted", kind="success")
                self.load()
            else:
                Toast.show(self, "Delete failed", kind="error")

    def on_shown(self):
        self.load()


class _InventoryArchiveTab(_BaseArchiveTab):
    _kind = "item"
    _name_key = "item_name"
    _columns = ("barcode", "item_name", "brand", "category", "qty",
                "min", "storage", "expires", "archived_at", "archived_by")
    _headers = ("Barcode", "Item Name", "Brand", "Category", "Qty", "Min",
                "Location", "Expires", "Archived", "By")
    _widths  = (130, 190, 90, 110, 60, 50, 90, 90, 140, 100)

    def _fetch(self, search: str = ""):
        return self.db.get_archived_inventory(search)

    def _restore(self, archive_id: int):
        return self.db.restore_archived_item(archive_id)

    def _delete(self, archive_id: int):
        return self.db.permanently_delete_archived_item(archive_id)

    def _row_values(self, item):
        return (
            item["barcode"],
            item["item_name"],
            item.get("brand") or "",
            item.get("category") or "",
            item["current_quantity"],
            item["minimum_stock"],
            item.get("storage_location") or "",
            item.get("expiration_date") or "",
            item.get("archived_at", "")[:16],
            item.get("archived_by") or "",
        )


class _ClientArchiveTab(_BaseArchiveTab):
    _kind = "client"
    _name_key = "first_name"
    _columns = ("name", "student_id", "email", "phone", "status", "archived_at", "archived_by")
    _headers = ("Name", "Student ID", "Email", "Phone", "Status", "Archived", "By")
    _widths  = (150, 120, 160, 120, 90, 140, 100)

    def _fetch(self, search: str = ""):
        return self.db.get_archived_clients(search)

    def _restore(self, archive_id: int):
        return self.db.restore_archived_client(archive_id)

    def _delete(self, archive_id: int):
        return self.db.permanently_delete_archived_client(archive_id)

    def _row_values(self, c):
        status = "Full-time" if c.get("enrollment_status") == "full_time" else "Part-time"
        return (
            f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
            c.get("student_id") or "",
            c.get("email") or "",
            c.get("phone") or "",
            status,
            c.get("archived_at", "")[:16],
            c.get("archived_by") or "",
        )


class _UserArchiveTab(_BaseArchiveTab):
    _kind = "user"
    _name_key = "username"
    _columns = ("username", "full_name", "role", "active", "archived_at", "archived_by")
    _headers = ("Username", "Full Name", "Role", "Active", "Archived", "By")
    _widths  = (140, 180, 90, 80, 140, 100)

    def _fetch(self, search: str = ""):
        return self.db.get_archived_users(search)

    def _restore(self, archive_id: int):
        return self.db.restore_archived_user(archive_id)

    def _delete(self, archive_id: int):
        return self.db.permanently_delete_archived_user(archive_id)

    def _row_values(self, u):
        return (
            u.get("username") or "",
            u.get("full_name") or "",
            u.get("role") or "",
            "Yes" if u.get("is_active") else "No",
            u.get("archived_at", "")[:16],
            u.get("archived_by") or "",
        )


class _TransactionArchiveTab(_BaseArchiveTab):
    _kind = "transaction"
    _name_key = "item_name"
    _columns = ("type", "barcode", "item_name", "category", "qty", "recipient", "username", "timestamp", "archived_at", "archived_by")
    _headers = ("Type", "Barcode", "Item", "Category", "Qty", "Recipient", "User", "Timestamp", "Archived", "By")
    _widths  = (80, 120, 170, 100, 50, 120, 100, 140, 140, 100)

    def _fetch(self, search: str = ""):
        return self.db.get_archived_transactions(search)

    def _restore(self, archive_id: int):
        return self.db.restore_archived_transaction(archive_id)

    def _delete(self, archive_id: int):
        return self.db.permanently_delete_archived_transaction(archive_id)

    def _row_values(self, t):
        return (
            t.get("transaction_type") or "",
            t.get("barcode") or "",
            t.get("item_name") or "",
            t.get("category") or "",
            t.get("quantity") or 0,
            t.get("recipient") or "",
            t.get("username") or "",
            t.get("timestamp") or "",
            t.get("archived_at", "")[:16],
            t.get("archived_by") or "",
        )


class ArchiveManager(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict, on_update=None, embedded=False):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self.user = user
        _apply_treeview_style()
        self._build()

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tabs = {}
        tabs = ctk.CTkTabview(
            self, fg_color=BG_PRIMARY, corner_radius=12,
            border_color=BORDER_COLOR, segmented_button_fg_color=BG_SECONDARY,
            segmented_button_selected_color=ACCENT_GOLD,
            segmented_button_selected_hover_color=ACCENT_GOLD,
            segmented_button_unselected_color=BG_SECONDARY,
            segmented_button_unselected_hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
        )
        tabs.grid(row=0, column=0, sticky="nsew", padx=24, pady=(16, 8))
        self._tabview = tabs

        for name, Tab in (
            ("Inventory",    _InventoryArchiveTab),
            ("Clients",      _ClientArchiveTab),
            ("Users",        _UserArchiveTab),
            ("Transactions", _TransactionArchiveTab),
        ):
            tab = tabs.add(name)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
            widget = Tab(tab, self.db, self.user)
            widget.grid(row=0, column=0, sticky="nsew")
            self._tabs[name] = widget

    def on_shown(self):
        current = self._tabview.get()
        tab = self._tabs.get(current)
        if tab and hasattr(tab, "on_shown"):
            tab.on_shown()
