import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

CLR_BG       = "#f0f4f8"
CLR_HEADER   = "#1a1a2e"
CLR_GREEN    = "#27ae60"
CLR_GREEN_H  = "#219a52"
CLR_RED      = "#e74c3c"
CLR_RED_H    = "#c0392b"
CLR_BLUE     = "#2980b9"
CLR_BLUE_H   = "#1a6fa8"
CLR_ORANGE   = "#e67e22"
CLR_PURPLE   = "#8e44ad"
CLR_PURPLE_H = "#7d3c98"
CLR_TEAL     = "#16a085"
CLR_GRAY     = "#7f8c8d"
CLR_GRAY_H   = "#626567"


class Dashboard(ctk.CTkFrame):
    def __init__(self, parent, user: dict, db, logout_cb):
        super().__init__(parent, fg_color=CLR_BG)
        self.user = user
        self.db = db
        self.logout_cb = logout_cb
        self._lookup_timer = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()
        self._refresh_badge()

    # ------------------------------------------------------------------
    # Header bar
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=CLR_HEADER, corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="📦  Inventory Control Center",
            font=ctk.CTkFont(size=19, weight="bold"), text_color="white",
        ).grid(row=0, column=0, padx=22, pady=14)

        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.grid(row=0, column=2, padx=18)

        ctk.CTkLabel(
            right,
            text=f"👤  {self.user['username']}  ({self.user['role'].title()})",
            text_color="#ccc", font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 16))

        ctk.CTkButton(
            right, text="Logout", width=80, height=30,
            fg_color=CLR_RED, hover_color=CLR_RED_H,
            command=self.logout_cb,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Body
    # ------------------------------------------------------------------

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=18)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._build_scan_panel(body)
        self._build_action_panel(body)

    # ------------------------------------------------------------------
    # Left – scan panel
    # ------------------------------------------------------------------

    def _build_scan_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Scan / Lookup",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=22, pady=(22, 14), sticky="w")

        # Barcode
        ctk.CTkLabel(panel, text="Barcode:", font=ctk.CTkFont(size=13)).grid(
            row=1, column=0, padx=22, pady=8, sticky="w")
        self.barcode_var = tk.StringVar()
        self.barcode_var.trace_add("write", self._on_barcode_change)
        self.barcode_entry = ctk.CTkEntry(
            panel, textvariable=self.barcode_var,
            placeholder_text="Click here, then scan barcode…",
            font=ctk.CTkFont(size=14), height=42,
        )
        self.barcode_entry.grid(row=1, column=1, padx=(0, 22), pady=8, sticky="ew")
        self.barcode_entry.bind("<Return>", lambda _e: self._auto_scan())

        # Quantity
        ctk.CTkLabel(panel, text="Quantity:", font=ctk.CTkFont(size=13)).grid(
            row=2, column=0, padx=22, pady=8, sticky="w")
        self.qty_var = tk.StringVar(value="1")
        ctk.CTkEntry(panel, textvariable=self.qty_var, width=110).grid(
            row=2, column=1, padx=(0, 22), pady=8, sticky="w")

        # Recipient
        ctk.CTkLabel(panel, text="Recipient:", font=ctk.CTkFont(size=13)).grid(
            row=3, column=0, padx=22, pady=8, sticky="w")
        self.recipient_var = tk.StringVar()
        self.recipient_entry = ctk.CTkEntry(
            panel, textvariable=self.recipient_var,
            placeholder_text="Required for Scan Out",
        )
        self.recipient_entry.grid(row=3, column=1, padx=(0, 22), pady=8, sticky="ew")

        ctk.CTkFrame(panel, height=1, fg_color="#dde1e7").grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=22, pady=12)

        # Item info display
        info_box = ctk.CTkFrame(panel, fg_color="#f7f9fb", corner_radius=8)
        info_box.grid(row=5, column=0, columnspan=2, sticky="ew", padx=22, pady=(0, 14))
        info_box.grid_columnconfigure(1, weight=1)

        self._info = {}
        for i, (lbl, key) in enumerate([
            ("Item Name:", "item_name"), ("Category:", "category"),
            ("Current Stock:", "current_qty"), ("Minimum Stock:", "min_stock"),
        ]):
            ctk.CTkLabel(info_box, text=lbl, font=ctk.CTkFont(size=12),
                         text_color="#555").grid(row=i, column=0, padx=16, pady=5, sticky="w")
            var = tk.StringVar(value="—")
            self._info[key] = var
            ctk.CTkLabel(info_box, textvariable=var,
                         font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=i, column=1, padx=16, pady=5, sticky="w")

        # Status
        self.status_var = tk.StringVar(value="READY")
        self.status_lbl = ctk.CTkLabel(
            panel, textvariable=self.status_var,
            font=ctk.CTkFont(size=15, weight="bold"), text_color=CLR_GREEN,
        )
        self.status_lbl.grid(row=6, column=0, columnspan=2, pady=14)

        # Buttons
        btns = ctk.CTkFrame(panel, fg_color="transparent")
        btns.grid(row=7, column=0, columnspan=2, pady=(0, 22))

        ctk.CTkButton(
            btns, text="✅  Scan In", width=155, height=46,
            fg_color=CLR_GREEN, hover_color=CLR_GREEN_H,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.scan_in,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btns, text="📤  Scan Out", width=155, height=46,
            fg_color=CLR_RED, hover_color=CLR_RED_H,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.scan_out,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btns, text="🔄  Clear", width=120, height=46,
            fg_color=CLR_BLUE, hover_color=CLR_BLUE_H,
            font=ctk.CTkFont(size=14, weight="bold"), command=self.clear_form,
        ).pack(side="left", padx=8)

        self.after(200, self.barcode_entry.focus)

    # ------------------------------------------------------------------
    # Right – action panel
    # ------------------------------------------------------------------

    def _build_action_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=12, width=210)
        panel.grid(row=0, column=1, sticky="ns")
        panel.grid_propagate(False)

        ctk.CTkLabel(panel, text="Actions",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(22, 8))

        self.badge_lbl = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont(size=11), text_color=CLR_RED)
        self.badge_lbl.pack(pady=(0, 14))

        nav = [
            ("➕  Add Item",            self.open_add_item,   CLR_PURPLE, CLR_PURPLE_H),
            ("📦  View Inventory",      self.open_inventory,  CLR_BLUE,   CLR_BLUE_H),
            ("📋  Transaction History", self.open_history,    CLR_TEAL,   "#138d75"),
            ("📊  Reports",             self.open_reports,    CLR_ORANGE, "#ca6f1e"),
        ]
        if self.user["role"] == "admin":
            nav.append(("👥  Manage Users", self.open_user_mgmt, CLR_GRAY, CLR_GRAY_H))

        for text, cmd, fg, hover in nav:
            ctk.CTkButton(
                panel, text=text, width=178, height=42, anchor="w",
                fg_color=fg, hover_color=hover, command=cmd,
            ).pack(pady=5, padx=16)

    # ------------------------------------------------------------------
    # Barcode lookup (debounced)
    # ------------------------------------------------------------------

    def _on_barcode_change(self, *_args):
        if self._lookup_timer:
            self.after_cancel(self._lookup_timer)
        barcode = self.barcode_var.get().strip()
        if len(barcode) >= 3:
            self._lookup_timer = self.after(350, self._lookup_now)
        elif not barcode:
            self._reset_info()

    def _lookup_now(self):
        barcode = self.barcode_var.get().strip()
        if not barcode:
            return
        item, direction = self.db.get_item_by_any_barcode(barcode)
        if item:
            self._info["item_name"].set(item["item_name"])
            self._info["category"].set(item["category"] or "—")
            self._info["current_qty"].set(str(item["current_quantity"]))
            self._info["min_stock"].set(str(item["minimum_stock"]))
            qty = item["current_quantity"]
            dir_tag = "  [→ AUTO SCAN IN]" if direction == "SCAN_IN" else "  [→ AUTO SCAN OUT]"
            if qty == 0:
                self._set_status("OUT OF STOCK" + dir_tag, CLR_RED)
            elif qty <= item["minimum_stock"]:
                self._set_status("LOW STOCK" + dir_tag, CLR_ORANGE)
            else:
                self._set_status("READY" + dir_tag, CLR_GREEN)
        else:
            self._reset_info()
            self._set_status("ITEM NOT FOUND", CLR_RED)

    def _auto_scan(self):
        """Called when Enter is pressed in the barcode field.
        Detects direction from barcode type and auto-executes.
        """
        barcode = self.barcode_var.get().strip()
        if not barcode:
            return
        item, direction = self.db.get_item_by_any_barcode(barcode)
        if not item:
            self._set_status("ITEM NOT FOUND", CLR_RED)
            return
        if direction == "SCAN_IN":
            self.scan_in()
        else:
            self.scan_out()

    # ------------------------------------------------------------------
    # Scan In / Scan Out
    # ------------------------------------------------------------------

    def scan_in(self):
        barcode, qty = self._validated_inputs(require_recipient=False)
        if barcode is None:
            return
        item = self.db.get_item_by_barcode(barcode)
        if not item:
            self._set_status("ITEM NOT FOUND", CLR_RED)
            return
        self.db.adjust_stock(barcode, qty)
        self.db.add_transaction(
            "SCAN_IN", barcode, item["item_name"],
            item["category"], qty, "", self.user["username"],
        )
        self._set_status(f"SUCCESS  ✔  +{qty}  {item['item_name']}", CLR_GREEN)
        self._refresh_badge()
        self.after(1800, self.clear_form)

    def scan_out(self):
        barcode, qty = self._validated_inputs(require_recipient=True)
        if barcode is None:
            return
        recipient = self.recipient_var.get().strip()
        item = self.db.get_item_by_barcode(barcode)
        if not item:
            self._set_status("ITEM NOT FOUND", CLR_RED)
            return
        if item["current_quantity"] == 0:
            self._set_status("OUT OF STOCK – cannot scan out", CLR_RED)
            return
        if item["current_quantity"] < qty:
            self._set_status(
                f"ERROR: Only {item['current_quantity']} in stock (requested {qty})", CLR_RED)
            return
        self.db.adjust_stock(barcode, -qty)
        self.db.add_transaction(
            "SCAN_OUT", barcode, item["item_name"],
            item["category"], qty, recipient, self.user["username"],
        )
        self._set_status(
            f"SUCCESS  ✔  -{qty}  {item['item_name']}  →  {recipient}", CLR_GREEN)
        self._refresh_badge()
        self.after(1800, self.clear_form)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validated_inputs(self, require_recipient: bool):
        """Return (barcode, qty) or (None, None) after setting an error status."""
        barcode = self.barcode_var.get().strip()
        if not barcode:
            self._set_status("ERROR: Scan or enter a barcode first", CLR_RED)
            return None, None
        if require_recipient and not self.recipient_var.get().strip():
            self._set_status("ERROR: Recipient name required for Scan Out", CLR_RED)
            self.recipient_entry.focus()
            return None, None
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            self._set_status("ERROR: Quantity must be a positive whole number", CLR_RED)
            return None, None
        return barcode, qty

    def _set_status(self, text: str, color: str):
        self.status_var.set(text)
        self.status_lbl.configure(text_color=color)

    def _reset_info(self):
        for var in self._info.values():
            var.set("—")
        self._set_status("READY", CLR_GREEN)

    def clear_form(self):
        self.barcode_var.set("")
        self.qty_var.set("1")
        self.recipient_var.set("")
        self._reset_info()
        self.barcode_entry.focus()

    def _refresh_badge(self):
        count = self.db.get_low_stock_count()
        if count:
            self.badge_lbl.configure(
                text=f"⚠️  {count} item(s) low / out of stock", text_color=CLR_RED)
        else:
            self.badge_lbl.configure(
                text="✅  All stock levels OK", text_color=CLR_GREEN)

    # ------------------------------------------------------------------
    # Window openers
    # ------------------------------------------------------------------

    def open_add_item(self):
        if self.user["role"] != "admin":
            messagebox.showwarning("Access Denied", "Only admins can add new items.")
            return
        from add_item_dialog import AddItemDialog
        AddItemDialog(self, self.db, self._refresh_badge)

    def open_inventory(self):
        from inventory_list import InventoryList
        InventoryList(self, self.db, self.user, self._refresh_badge)

    def open_history(self):
        from transaction_history import TransactionHistory
        TransactionHistory(self, self.db)

    def open_reports(self):
        from reports import Reports
        Reports(self, self.db)

    def open_user_mgmt(self):
        from user_management import UserManagement
        UserManagement(self, self.db)
