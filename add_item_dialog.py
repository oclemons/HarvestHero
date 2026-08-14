import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk


class AddItemDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.on_complete = on_complete
        self.title("Add New Inventory Item")
        self.geometry("500x600")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)
        self._load_storage_locations()

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

        # Storage location dropdown
        ctk.CTkLabel(form, text="Storage Location", anchor="w").grid(
            row=len(fields), column=0, padx=16, pady=8, sticky="w")
        self.storage_var = tk.StringVar(value="")
        self.storage_menu = ctk.CTkOptionMenu(form, variable=self.storage_var, values=[])
        self.storage_menu.grid(row=len(fields), column=1, padx=(0, 16), pady=8, sticky="ew")

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

    def _load_storage_locations(self):
        """Load available storage locations from database."""
        try:
            # Get all items and extract unique storage locations
            all_items = self.db.get_all_items()
            locations = sorted(set(
                item["storage_location"] 
                for item in all_items 
                if item.get("storage_location")
            ))
            self.storage_menu.configure(values=locations)
            if locations:
                self.storage_var.set(locations[0])
        except Exception:
            pass

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
        storage_location = self.storage_var.get().strip()
        
        ok, msg = self.db.add_item(barcode, item_name, category, qty, min_stock, notes, barcode_out)
        if ok:
            # Update storage location if provided
            if storage_location:
                try:
                    conn = self.db._connect()
                    conn.execute(
                        "UPDATE inventory_items SET storage_location = ? WHERE barcode = ?",
                        (storage_location, barcode)
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Error updating storage location: {e}")
            
            messagebox.showinfo("Item Added",
                                f"'{item_name}' has been added to inventory.")
            if self.on_complete:
                self.on_complete()
            self.destroy()
        else:
            self.status_lbl.configure(text=msg)
