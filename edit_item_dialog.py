import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk


class EditItemDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, item: dict, user: dict = None, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.item = item
        self.user = user or {}
        self.on_complete = on_complete
        self.is_admin = self.user.get("role") == "admin"
        self.title(f"Edit Item – {item['item_name']}")
        self.geometry("460x520")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)
        self._load_storage_locations()

    # ------------------------------------------------------------------

    def _build(self):
        title_text = "Edit Item Details"
        if not self.is_admin:
            title_text += " (Read-Only)"
        
        ctk.CTkLabel(
            self, text=title_text,
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(pady=(24, 16))

        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=28, pady=(0, 14))
        form.grid_columnconfigure(1, weight=1)

        # Barcode field - editable for admin, read-only for staff
        ctk.CTkLabel(form, text="Barcode (SCAN_IN):", anchor="w").grid(
            row=0, column=0, padx=14, pady=8, sticky="w")
        
        if self.is_admin:
            # Admin can edit barcode
            barcode_var = tk.StringVar(value=self.item["barcode"])
            self._vars = {"barcode": barcode_var}
            ctk.CTkEntry(form, textvariable=barcode_var).grid(
                row=0, column=1, padx=(0, 14), pady=8, sticky="ew")
        else:
            # Staff sees read-only barcode
            ctk.CTkLabel(
                form, text=self.item["barcode"],
                font=ctk.CTkFont(weight="bold"),
            ).grid(row=0, column=1, padx=14, pady=8, sticky="w")
            self._vars = {}

        fields = [
            ("Item Name *",     "item_name",   self.item["item_name"]),
            ("Category",        "category",    self.item["category"]),
            ("Scan-Out Barcode","barcode_out", self.item.get("barcode_out") or ""),
            ("Minimum Stock",   "min_stock",   str(self.item["minimum_stock"])),
            ("Current Stock",   "current_qty", str(self.item["current_quantity"])),
            ("Notes",           "notes",       self.item["notes"]),
            ("Storage Location","storage_location", self.item.get("storage_location") or ""),
        ]

        for i, (label, key, value) in enumerate(fields, start=1):
            ctk.CTkLabel(form, text=label, anchor="w").grid(
                row=i, column=0, padx=14, pady=8, sticky="w")
            var = tk.StringVar(value=value)
            self._vars[key] = var
            
            if self.is_admin:
                # Admin can edit all fields
                ctk.CTkEntry(form, textvariable=var).grid(
                    row=i, column=1, padx=(0, 14), pady=8, sticky="ew")
            else:
                # Staff sees read-only fields
                entry = ctk.CTkEntry(form, textvariable=var, state="disabled")
                entry.grid(row=i, column=1, padx=(0, 14), pady=8, sticky="ew")

        self.status_lbl = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.status_lbl.pack(pady=(2, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(8, 22))

        if self.is_admin:
            ctk.CTkButton(
                btn_row, text="Save Changes", width=140, height=40,
                fg_color="#27ae60", hover_color="#219a52",
                command=self._save,
            ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row, text="Close", width=110, height=40,
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
            # Update the storage_location field if it's a dropdown
            if "storage_location" in self._vars and hasattr(self, 'storage_menu'):
                self.storage_menu.configure(values=locations)
        except Exception:
            pass

    def _save(self):
        if not self.is_admin:
            messagebox.showwarning("Read-Only", "Staff accounts cannot edit items.")
            return
        
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

        # Check if barcode was changed and validate uniqueness
        new_barcode = self._vars.get("barcode", tk.StringVar()).get().strip()
        if new_barcode and new_barcode != self.item["barcode"]:
            # Check if new barcode already exists
            existing = self.db.get_item_by_barcode(new_barcode)
            if existing and existing["id"] != self.item["id"]:
                self.status_lbl.configure(text="Barcode already exists.")
                return
            # Update barcode in database
            try:
                conn = self.db._connect()
                conn.execute(
                    "UPDATE inventory_items SET barcode = ? WHERE id = ?",
                    (new_barcode, self.item["id"])
                )
                conn.commit()
                conn.close()
            except Exception as e:
                self.status_lbl.configure(text=f"Error updating barcode: {str(e)}")
                return

        self.db.update_item(
            self.item["id"], item_name,
            self._vars["category"].get().strip(),
            min_stock,
            self._vars["notes"].get().strip(),
            self._vars["barcode_out"].get().strip(),
        )
        self.db.set_stock(self.item["id"], current_qty)
        
        # Update storage location if provided
        storage_location = self._vars.get("storage_location", tk.StringVar()).get().strip()
        if storage_location:
            try:
                conn = self.db._connect()
                conn.execute(
                    "UPDATE inventory_items SET storage_location = ? WHERE id = ?",
                    (storage_location, self.item["id"])
                )
                conn.commit()
                conn.close()
            except Exception as e:
                self.status_lbl.configure(text=f"Error updating storage location: {str(e)}")
                return

        messagebox.showinfo("Saved", f"'{item_name}' updated successfully.")
        if self.on_complete:
            self.on_complete()
        self.destroy()
