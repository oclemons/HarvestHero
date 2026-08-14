"""shopping_list_screen.py — Ava's auto-generated shopping list.

Every SCAN_OUT adds the sold quantity to an item's running "need" total;
every SCAN_IN (restock) subtracts it back off. This screen shows that
running list and lets the user adjust quantities, remove items once
purchased, or clear the whole list.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER, BG_ELEVATED,
    ACCENT, ACCENT_HOVER, ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR,
)
from toast import Toast


class ShoppingListScreen(ctk.CTkFrame):
    def __init__(self, parent, db, embedded=False):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self._build()
        self.load()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---- title ----
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 2))
        ctk.CTkLabel(
            title_row, text="Shopping List",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text="Ava automatically adds items here as they're scanned "
                 "out, and removes them as they're restocked. Adjust "
                 "quantities or check items off once purchased.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))

        # ---- treeview card ----
        tf = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        tf.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 8))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("Shop.Treeview",
                rowheight=30, font=(FONT_FAMILY, 11),
                background=BG_SECONDARY, fieldbackground=BG_SECONDARY,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Shop.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_CARD, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Shop.Treeview",
                background=[("selected", ACCENT)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        cols = ("item_name", "category", "quantity_needed", "updated_at")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 style="Shop.Treeview")
        for col, heading, width in [
            ("item_name",       "Item",         260),
            ("category",        "Category",     150),
            ("quantity_needed", "Qty Needed",   110),
            ("updated_at",      "Last Updated", 160),
        ]:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=60,
                              anchor="center" if col == "quantity_needed" else "w")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # ---- action bar ----
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 8))

        ctk.CTkLabel(
            actions, text="Qty:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 6))

        self.qty_var = tk.StringVar()
        ctk.CTkEntry(
            actions, textvariable=self.qty_var, width=70, height=34,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions, text="Update Qty", width=110, height=34, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
            command=self._update_qty,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            actions, text="Mark Purchased / Remove", width=190, height=34,
            corner_radius=8, fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white", command=self._remove_selected,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            actions, text="Clear All", width=90, height=34, corner_radius=8,
            fg_color=BG_SECONDARY, hover_color=ACCENT_RED,
            text_color=TEXT_MUTED, command=self._clear_all,
        ).pack(side="left")

        ctk.CTkButton(
            actions, text="Auto-Populate Low Stock", width=180, height=34, corner_radius=8,
            fg_color=ACCENT_GOLD, hover_color="#FF9500",
            text_color="white", command=self._auto_populate_low_stock,
        ).pack(side="right", padx=(0, 6))

        ctk.CTkButton(
            actions, text="Refresh", width=90, height=34, corner_radius=8,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_COLOR,
            command=self.load,
        ).pack(side="right")

        self.count_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.count_lbl.grid(row=4, column=0, pady=(0, 10))

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def on_shown(self):
        self.load()

    def load(self):
        self._rows_by_iid = {}
        for r in self.tree.get_children():
            self.tree.delete(r)
        rows = self.db.get_shopping_list()
        for row in rows:
            iid = str(row["id"])
            self._rows_by_iid[iid] = row
            self.tree.insert("", "end", iid=iid, values=(
                row["item_name"], row["category"] or "—",
                row["quantity_needed"], row["updated_at"],
            ))
        total_units = sum(r["quantity_needed"] for r in rows)
        self.count_lbl.configure(
            text=f"{len(rows)} item(s) · {total_units} unit(s) needed"
            if rows else "Nothing needed right now — inventory looks healthy!")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _selected_row(self):
        sel = self.tree.selection()
        if not sel:
            Toast.show(self, "Select an item first", kind="warning")
            return None
        return self._rows_by_iid.get(sel[0])

    def _update_qty(self):
        row = self._selected_row()
        if row is None:
            return
        try:
            qty = int(self.qty_var.get().strip())
            if qty < 0:
                raise ValueError
        except ValueError:
            Toast.show(self, "Enter a valid non-negative quantity", kind="warning")
            return
        self.db.update_shopping_list_quantity(row["id"], qty)
        self.qty_var.set("")
        self.load()
        Toast.show(self, f"Updated {row['item_name']}", kind="success")

    def _remove_selected(self):
        row = self._selected_row()
        if row is None:
            return
        self.db.remove_shopping_list_item(row["id"])
        self.load()
        Toast.show(self, f"Removed {row['item_name']} from the list", kind="success")

    def _clear_all(self):
        if not messagebox.askyesno(
            "Clear Shopping List",
            "This will remove all items from the shopping list. Continue?",
            icon="warning",
        ):
            return
        self.db.clear_shopping_list()
        self.load()
        Toast.show(self, "Shopping list cleared", kind="success")

    def _auto_populate_low_stock(self):
        """Automatically add all low-stock items to the shopping list."""
        try:
            # Get all low-stock items using database method
            low_stock_items = self.db.get_low_stock_items()
            
            if not low_stock_items:
                Toast.show(self, "No low-stock items found", kind="info")
                return
            
            # Add each low-stock item to shopping list
            added_count = 0
            for item in low_stock_items:
                # Calculate quantity needed to reach minimum
                qty_needed = item["minimum_stock"] - item["current_quantity"]
                
                # Add to shopping list using database method
                # Use _apply_shopping_list_delta to add the item
                self.db._apply_shopping_list_delta(
                    barcode=item["barcode"],
                    item_name=item["item_name"],
                    category=item.get("category", ""),
                    delta=qty_needed
                )
                added_count += 1
            
            self.load()
            Toast.show(self, f"Added {added_count} low-stock item(s) to shopping list", kind="success")
        except Exception as e:
            Toast.show(self, f"Error: {str(e)}", kind="error")
            print(f"Auto-populate error: {e}")
