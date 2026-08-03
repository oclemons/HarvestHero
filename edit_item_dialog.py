import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk


class EditItemDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, item: dict, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.item = item
        self.on_complete = on_complete
        self.title(f"Edit Item – {item['item_name']}")
        self.geometry("460x460")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    # ------------------------------------------------------------------

    def _build(self):
        ctk.CTkLabel(
            self, text="Edit Item Details",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(pady=(24, 16))

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=28, pady=(0, 14))
        form.grid_columnconfigure(1, weight=1)

        # Read-only barcode display
        ctk.CTkLabel(form, text="Barcode:", anchor="w").grid(
            row=0, column=0, padx=14, pady=8, sticky="w")
        ctk.CTkLabel(
            form, text=self.item["barcode"],
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=1, padx=14, pady=8, sticky="w")

        fields = [
            ("Item Name *",     "item_name",   self.item["item_name"]),
            ("Category",        "category",    self.item["category"]),
            ("Scan-Out Barcode","barcode_out", self.item.get("barcode_out") or ""),
            ("Minimum Stock",   "min_stock",   str(self.item["minimum_stock"])),
            ("Current Stock",   "current_qty", str(self.item["current_quantity"])),
            ("Notes",           "notes",       self.item["notes"]),
        ]

        self._vars = {}
        for i, (label, key, value) in enumerate(fields, start=1):
            ctk.CTkLabel(form, text=label, anchor="w").grid(
                row=i, column=0, padx=14, pady=8, sticky="w")
            var = tk.StringVar(value=value)
            self._vars[key] = var
            ctk.CTkEntry(form, textvariable=var).grid(
                row=i, column=1, padx=(0, 14), pady=8, sticky="ew")

        self.status_lbl = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.status_lbl.pack(pady=(2, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(8, 22))

        ctk.CTkButton(
            btn_row, text="Save Changes", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=self._save,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        ).pack(side="left", padx=10)

    # ------------------------------------------------------------------

    def _save(self):
        item_name = self._vars["item_name"].get().strip()
        if not item_name:
            self.status_lbl.configure(text="Item Name is required.")
            return

        try:
            min_stock   = int(self._vars["min_stock"].get() or "0")
            current_qty = int(self._vars["current_qty"].get() or "0")
            if min_stock < 0 or current_qty < 0:
                raise ValueError
        except ValueError:
            self.status_lbl.configure(
                text="Stock values must be non-negative whole numbers.")
            return

        self.db.update_item(
            self.item["id"], item_name,
            self._vars["category"].get().strip(),
            min_stock,
            self._vars["notes"].get().strip(),
            self._vars["barcode_out"].get().strip(),
        )
        self.db.set_stock(self.item["id"], current_qty)

        messagebox.showinfo("Saved", f"'{item_name}' updated successfully.")
        if self.on_complete:
            self.on_complete()
        self.destroy()
