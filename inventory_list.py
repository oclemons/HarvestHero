import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER, BG_ELEVATED,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
)
from glass_effects import create_glass_button


def _apply_treeview_style():
    """Apply harvest-themed treeview styling with glass effects."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Treeview",
                    rowheight=30, font=(FONT_FAMILY, 10),
                    background=BG_SECONDARY, fieldbackground=BG_SECONDARY,
                    foreground=TEXT_PRIMARY, borderwidth=1, relief="solid")
    style.configure("Treeview.Heading",
                    font=(FONT_FAMILY, 10, "bold"),
                    background=BG_ELEVATED, foreground=ACCENT_GOLD,
                    relief="flat", padding=6, borderwidth=1)
    style.map("Treeview",
              background=[("selected", ACCENT_BLUE)],
              foreground=[("selected", "white")],
              fieldbackground=[("selected", ACCENT_BLUE)])


class InventoryList(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict, on_update=None, embedded=False):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self.user = user
        self.on_update = on_update
        self._view_mode = "list"  # "list" or "pantry"
        self._pantry_view = None
        self._list_view = None
        _apply_treeview_style()
        self._build()
        self.load_items()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---- top bar ----
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            top, text="Inventory",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 20))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_items())
        ctk.CTkEntry(
            top, textvariable=self.search_var, width=300, height=36,
            placeholder_text="Search barcode, name, or category…",
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            top, text="↻ Refresh", width=90, height=36,
            fg_color=BG_SECONDARY, hover_color=BG_CARD,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self.load_items,
        ).pack(side="left", padx=4)

        # View toggle buttons
        ctk.CTkButton(
            top, text="📋 List View", width=100, height=36,
            fg_color=ACCENT_BLUE, hover_color="#1d4ed8",
            text_color="white", corner_radius=8,
            command=self._switch_to_list,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            top, text="🏪 Pantry View", width=120, height=36,
            fg_color=BG_SECONDARY, hover_color=BG_CARD,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self._switch_to_pantry,
        ).pack(side="right", padx=4)

        if self.user["role"] == "admin":
            ctk.CTkButton(
                top, text="+ Add Item", width=100, height=36,
                fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
                text_color="#1B1F24", corner_radius=8,
                command=self._add_item,
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                top, text="📥 Bulk Import", width=120, height=36,
                fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
                text_color="#1B1F24", corner_radius=8,
                command=self._bulk_import_barcodes,
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                top, text="🏠 Manage Shelves", width=140, height=36,
                fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
                text_color="#1B1F24", corner_radius=8,
                command=self._manage_shelves,
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                top, text="Archive", width=90, height=36,
                fg_color=ACCENT_RED, hover_color="#b91c1c",
                text_color="white", corner_radius=8,
                command=self.delete_selected,
            ).pack(side="right", padx=4)
            ctk.CTkButton(
                top, text="✎ Edit", width=90, height=36,
                fg_color=ACCENT_BLUE, hover_color="#1d4ed8",
                text_color="white", corner_radius=8,
                command=self.edit_selected,
            ).pack(side="right", padx=4)

        # ---- content container ----
        self.content_container = ctk.CTkFrame(self, fg_color=BG_PRIMARY)
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 8))
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # ---- treeview (list view) ----
        tree_frame = ctk.CTkFrame(self.content_container, fg_color=BG_CARD, corner_radius=12)
        tree_frame.grid(row=0, column=0, sticky="nsew")

        cols = ("barcode", "item_name", "brand", "category", "current_qty",
                "min_stock", "status", "storage", "expires", "notes")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                 show="headings", selectmode="browse")

        headers = [
            ("barcode",     "Barcode",       130),
            ("item_name",   "Item Name",     190),
            ("brand",       "Brand",          90),
            ("category",    "Category",      110),
            ("current_qty", "Qty",            60),
            ("min_stock",   "Min",            50),
            ("status",      "Status",        110),
            ("storage",     "Location",       90),
            ("expires",     "Expires",         90),
            ("notes",       "Notes",         130),
        ]
        for col, heading, width in headers:
            self.tree.heading(col, text=heading,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, minwidth=50)

        self.tree.tag_configure("out",      background="#3b1515", foreground="#fca5a5")
        self.tree.tag_configure("low",      background="#3b2f0e", foreground="#fcd34d")
        self.tree.tag_configure("ok",       background=BG_SECONDARY, foreground=TEXT_PRIMARY)
        self.tree.tag_configure("expired",  background="#2d0f0f", foreground="#ff6b6b")
        self.tree.tag_configure("exp_soon", background="#2d2000", foreground="#fbbf24")
        self.tree.tag_configure("overstock", background="#3b2d5e", foreground="#a78bfa")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._list_view = tree_frame

        self.tree.bind("<Double-1>", lambda _e: self.edit_selected()
                       if self.user["role"] == "admin" else None)

        self.count_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.count_lbl.grid(row=2, column=0, pady=(0, 12))

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_items(self):
        search = self.search_var.get().strip()
        items  = self.db.get_all_items(search)

        for row in self.tree.get_children():
            self.tree.delete(row)

        import datetime
        today = datetime.date.today()
        for item in items:
            qty  = item["current_quantity"]
            mins = item["minimum_stock"]
            exp  = item.get("expiration_date", "") or ""

            # Expiration state
            exp_tag = None
            if exp:
                try:
                    exp_d = datetime.date.fromisoformat(exp)
                    diff  = (exp_d - today).days
                    if diff < 0:
                        exp_tag = "expired"
                        exp     = f"EXPIRED ({exp})"
                    elif diff <= 14:
                        exp_tag = "exp_soon"
                        exp     = f"{exp} ({diff}d)"
                except Exception:
                    pass

            # Stock state
            if exp_tag == "expired":
                status, tag = "EXPIRED", "expired"
            elif qty == 0:
                status, tag = "OUT OF STOCK", "out"
            elif qty <= mins:
                status, tag = "LOW STOCK", "low"
            elif exp_tag == "exp_soon":
                status, tag = "EXPIRING SOON", "exp_soon"
            elif mins > 0 and qty > (mins * 2.5):
                status, tag = "OVERSTOCK", "overstock"
            else:
                status, tag = "OK", "ok"

            self.tree.insert(
                "", "end", iid=str(item["id"]),
                values=(
                    item["barcode"],
                    item["item_name"],
                    item.get("brand") or "",
                    item.get("category") or "",
                    qty, mins, status,
                    item.get("storage_location") or "",
                    exp,
                    item.get("notes") or "",
                ),
                tags=(tag,),
            )

        self.count_lbl.configure(text=f"{len(items)} item(s) found")

    # ------------------------------------------------------------------
    # Sort
    # ------------------------------------------------------------------

    _sort_state: dict = {}

    def _sort_by(self, col: str):
        reverse = self._sort_state.get(col, False)
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            data.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (_, k) in enumerate(data):
            self.tree.move(k, "", index)
        self._sort_state[col] = not reverse

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def on_shown(self):
        self.load_items()

    def _add_item(self):
        from add_item_dialog import AddItemDialog
        AddItemDialog(self, self.db, on_complete=self.load_items)

    def _bulk_import_barcodes(self):
        from barcode_importer import BarcodeImporterDialog
        BarcodeImporterDialog(self, self.db, on_complete=self.load_items)

    def _manage_shelves(self):
        from shelf_manager import ShelfManagerDialog
        ShelfManagerDialog(self, self.db, on_complete=self.load_items)

    def _selected_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select an item first.")
            return None
        item_id = int(sel[0])
        # Query the row directly instead of scanning the full inventory
        # for a match; O(1) vs O(n).
        try:
            return self.db.get_item_by_id(item_id)
        except AttributeError:
            # Older ApiClient without the helper — fall back gracefully.
            for item in self.db.get_all_items():
                if item["id"] == item_id:
                    return item
            return None

    def edit_selected(self):
        item = self._selected_item()
        if not item:
            return
        from edit_item_dialog import EditItemDialog
        EditItemDialog(self, self.db, item, self.user, self._after_edit)

    def _after_edit(self):
        self.load_items()
        if self.on_update:
            self.on_update()

    def delete_selected(self):
        item = self._selected_item()
        if not item:
            return
        if messagebox.askyesno(
            "Confirm Archive",
            f"Archive '{item['item_name']}'?\n\nIt will be removed from active inventory "
            "and can be restored later from the Archive Manager.",
        ):
            self.db.archive_inventory_item(item["id"], archived_by=self.user.get("username", ""))
            self.load_items()
            if self.on_update:
                self.on_update()

    # ------------------------------------------------------------------
    # View switching
    # ------------------------------------------------------------------

    def _switch_to_list(self):
        """Switch to list view."""
        if self._view_mode == "list":
            return

        self._view_mode = "list"

        # Hide pantry view
        if self._pantry_view:
            self._pantry_view.grid_forget()

        # Show list view
        self._list_view.grid(row=0, column=0, sticky="nsew")
        self.load_items()

    def _switch_to_pantry(self):
        """Switch to pantry view."""
        if self._view_mode == "pantry":
            return

        self._view_mode = "pantry"

        # Hide list view
        self._list_view.grid_forget()

        # Create pantry view if needed
        if not self._pantry_view:
            from interactive_pantry_ui import InteractivePantryUI
            self._pantry_view = InteractivePantryUI(
                self.content_container, self.db, self.user,
            )

        self._pantry_view.grid(row=0, column=0, sticky="nsew")
        self._pantry_view.load_pantry()

    def _on_pantry_item_click(self, item: dict):
        """Handle item click from pantry view."""
        # Switch to list view and select the item
        self._switch_to_list()
        # Find and select the item in the tree
        for iid in self.tree.get_children():
            if int(iid) == item["id"]:
                self.tree.selection_set(iid)
                self.tree.see(iid)
                break
