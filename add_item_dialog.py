import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk


class AddItemDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.on_complete = on_complete
        self.title("Add New Inventory Item")
        self.geometry("500x530")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    # ------------------------------------------------------------------

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Add New Inventory Item",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(28, 20))

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=30, pady=(0, 16))
        form.grid_columnconfigure(1, weight=1)

        fields = [
            ("Scan-In Barcode *", "barcode",     "Scan or type the IN barcode",   ""),
            ("Scan-Out Barcode",  "barcode_out", "Scan or type the OUT barcode",  ""),
            ("Item Name *",       "item_name",   "Enter item name",               ""),
            ("Category",          "category",    "e.g. Electronics, Clothing",    ""),
            ("Starting Quantity", "quantity",    "0",                             "0"),
            ("Minimum Stock",     "min_stock",   "0",                             "0"),
            ("Notes",             "notes",       "Optional notes",                ""),
        ]

        self._vars = {}
        for i, (label, key, placeholder, default) in enumerate(fields):
            ctk.CTkLabel(form, text=label, anchor="w").grid(
                row=i, column=0, padx=16, pady=8, sticky="w")
            var = tk.StringVar(value=default)
            self._vars[key] = var
            ctk.CTkEntry(form, textvariable=var,
                         placeholder_text=placeholder).grid(
                row=i, column=1, padx=(0, 16), pady=8, sticky="ew")

        self.status_lbl = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.status_lbl.pack(pady=(4, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(8, 24))

        ctk.CTkButton(
            btn_row, text="Add Item", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=self._submit,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        ).pack(side="left", padx=10)

    # ------------------------------------------------------------------

    def _submit(self):
        barcode   = self._vars["barcode"].get().strip()
        item_name = self._vars["item_name"].get().strip()
        category  = self._vars["category"].get().strip()
        notes     = self._vars["notes"].get().strip()

        if not barcode:
            self.status_lbl.configure(text="Barcode is required.")
            return
        if not item_name:
            self.status_lbl.configure(text="Item Name is required.")
            return

        try:
            qty       = int(self._vars["quantity"].get() or "0")
            min_stock = int(self._vars["min_stock"].get() or "0")
            if qty < 0 or min_stock < 0:
                raise ValueError
        except ValueError:
            self.status_lbl.configure(
                text="Starting Quantity and Minimum Stock must be non-negative whole numbers.")
            return

        barcode_out = self._vars["barcode_out"].get().strip()
        ok, msg = self.db.add_item(barcode, item_name, category, qty, min_stock, notes, barcode_out)
        if ok:
            messagebox.showinfo("Item Added",
                                f"'{item_name}' has been added to inventory.")
            if self.on_complete:
                self.on_complete()
            self.destroy()
        else:
            self.status_lbl.configure(text=msg)
