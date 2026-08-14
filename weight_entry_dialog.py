"""weight_entry_dialog.py — Weight entry dialog for manual pounds tracking.

Allows admins to enter:
- Current Inventory Pounds
- Pounds Donated
- Pounds Discarded
- Auto-calculates Remaining Pounds
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime


class WeightEntryDialog(ctk.CTkToplevel):
    """Dialog for entering weight/pounds data."""

    def __init__(self, parent, db, item: dict, user: dict = None, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.item = item
        self.user = user or {}
        self.on_complete = on_complete
        self.title(f"Weight Entry – {item['item_name']}")
        self.geometry("500x550")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the weight entry dialog."""
        # Title
        ctk.CTkLabel(
            self, text="Weight/Pounds Entry",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 10))

        # Item info
        ctk.CTkLabel(
            self, text=f"Item: {self.item['item_name']}",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 20))

        # Form frame
        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=30, pady=(0, 16))
        form.grid_columnconfigure(1, weight=1)

        # Current Inventory Pounds
        ctk.CTkLabel(form, text="Current Inventory Pounds:", anchor="w").grid(
            row=0, column=0, padx=12, pady=12, sticky="w")
        self.current_var = tk.StringVar(value=str(self.item.get("current_pounds", 0.0)))
        ctk.CTkEntry(form, textvariable=self.current_var).grid(
            row=0, column=1, padx=(0, 12), pady=12, sticky="ew")

        # Pounds Donated
        ctk.CTkLabel(form, text="Pounds Donated:", anchor="w").grid(
            row=1, column=0, padx=12, pady=12, sticky="w")
        self.donated_var = tk.StringVar(value=str(self.item.get("donated_pounds", 0.0)))
        ctk.CTkEntry(form, textvariable=self.donated_var).grid(
            row=1, column=1, padx=(0, 12), pady=12, sticky="ew")

        # Pounds Discarded
        ctk.CTkLabel(form, text="Pounds Discarded:", anchor="w").grid(
            row=2, column=0, padx=12, pady=12, sticky="w")
        self.discarded_var = tk.StringVar(value=str(self.item.get("discarded_pounds", 0.0)))
        ctk.CTkEntry(form, textvariable=self.discarded_var).grid(
            row=2, column=1, padx=(0, 12), pady=12, sticky="ew")

        # Calculated Remaining (read-only)
        ctk.CTkLabel(form, text="Calculated Remaining:", anchor="w").grid(
            row=3, column=0, padx=12, pady=12, sticky="w")
        self.remaining_label = ctk.CTkLabel(
            form, text="0.0 lbs",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#27ae60"
        )
        self.remaining_label.grid(row=3, column=1, padx=(0, 12), pady=12, sticky="w")

        # Notes
        ctk.CTkLabel(form, text="Notes:", anchor="w").grid(
            row=4, column=0, padx=12, pady=12, sticky="nw")
        self.notes_var = tk.StringVar(value=self.item.get("notes", ""))
        notes_entry = ctk.CTkTextbox(form, height=80)
        notes_entry.grid(row=4, column=1, padx=(0, 12), pady=12, sticky="ew")
        notes_entry.insert("1.0", self.notes_var.get())
        self.notes_entry = notes_entry

        # Last Updated info
        self.info_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=9),
            text_color="#999"
        )
        self.info_label.pack(pady=(0, 10))

        # Status label
        self.status_lbl = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.status_lbl.pack(pady=(0, 10))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="Save", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=self._save,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        ).pack(side="left", padx=10)

        # Bind changes to update calculation
        self.current_var.trace_add("write", self._update_calculation)
        self.donated_var.trace_add("write", self._update_calculation)
        self.discarded_var.trace_add("write", self._update_calculation)

        # Initial calculation
        self._update_calculation()
        self._update_info()

    def _update_calculation(self, *args):
        """Update the calculated remaining pounds."""
        try:
            current = float(self.current_var.get() or 0.0)
            donated = float(self.donated_var.get() or 0.0)
            discarded = float(self.discarded_var.get() or 0.0)
            
            remaining = current + donated - discarded
            self.remaining_label.configure(text=f"{remaining:.2f} lbs")
        except ValueError:
            self.remaining_label.configure(text="Invalid input")

    def _update_info(self):
        """Update the info label with last updated info."""
        updated_at = self.item.get("updated_at", "")
        if updated_at:
            self.info_label.configure(text=f"Last updated: {updated_at}")

    def _save(self):
        """Save the weight data."""
        try:
            current = float(self.current_var.get() or 0.0)
            donated = float(self.donated_var.get() or 0.0)
            discarded = float(self.discarded_var.get() or 0.0)
            
            if current < 0 or donated < 0 or discarded < 0:
                self.status_lbl.configure(text="Values must be non-negative")
                return
            
            notes = self.notes_entry.get("1.0", "end").strip()
            username = self.user.get("username", "unknown")
            
            ok, msg = self.db.update_item_weights(
                self.item["id"], current, donated, discarded, notes, username
            )
            
            if ok:
                messagebox.showinfo("Saved", f"Weights updated for {self.item['item_name']}")
                if self.on_complete:
                    self.on_complete()
                self.destroy()
            else:
                self.status_lbl.configure(text=msg)
        except ValueError:
            self.status_lbl.configure(text="Please enter valid numbers")
