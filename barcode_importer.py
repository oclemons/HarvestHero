"""barcode_importer.py — Bulk barcode import dialog for admin users.

Supports:
- CSV file upload (columns: barcode, barcode_out, item_name)
- Paste text import (format: barcode|barcode_out|item_name, one per line)
- Preview and validation before importing
- Update existing items or create new ones
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import csv
from typing import List, Tuple


class BarcodeImporterDialog(ctk.CTkToplevel):
    """Dialog for bulk importing barcodes."""

    def __init__(self, parent, db, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.on_complete = on_complete
        self.title("Bulk Import Barcodes")
        self.geometry("700x600")
        self.resizable(True, True)
        self.grab_set()
        self._build()
        self.after(100, self.lift)

    def _build(self):
        """Build the import dialog UI."""
        # Title
        ctk.CTkLabel(
            self, text="Bulk Import Barcodes",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 10))

        # Instructions
        ctk.CTkLabel(
            self,
            text="Import barcodes via CSV file or paste text.\n"
                 "Format: barcode|barcode_out|item_name (one per line)",
            font=ctk.CTkFont(size=11),
            justify="left",
        ).pack(pady=(0, 20), padx=20)

        # Tab-like buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.csv_btn = ctk.CTkButton(
            button_frame, text="📁 Import CSV", width=150, height=36,
            command=self._import_csv
        )
        self.csv_btn.pack(side="left", padx=(0, 10))

        self.paste_btn = ctk.CTkButton(
            button_frame, text="📋 Paste Text", width=150, height=36,
            command=self._show_paste_dialog
        )
        self.paste_btn.pack(side="left")

        # Preview area
        ctk.CTkLabel(
            self, text="Preview:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.preview_text = ctk.CTkTextbox(self, height=250)
        self.preview_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.preview_text.configure(state="disabled")

        # Status label
        self.status_lbl = ctk.CTkLabel(
            self, text="", text_color="#e74c3c", font=ctk.CTkFont(size=10)
        )
        self.status_lbl.pack(pady=(0, 10))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(0, 20), padx=20, fill="x")
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row, text="Import", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=self._import_data,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_row, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        ).pack(side="right")

        self.import_data = []

    def _import_csv(self):
        """Import from CSV file."""
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            self.import_data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                # Skip header if present
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        barcode = row[0].strip()
                        barcode_out = row[1].strip()
                        item_name = row[2].strip()
                        if barcode and item_name:
                            self.import_data.append((barcode, barcode_out, item_name))

            self._show_preview()
        except Exception as e:
            self.status_lbl.configure(text=f"Error reading file: {str(e)}")

    def _show_paste_dialog(self):
        """Show paste dialog for text input."""
        paste_window = ctk.CTkToplevel(self)
        paste_window.title("Paste Barcodes")
        paste_window.geometry("500x400")
        paste_window.grab_set()

        ctk.CTkLabel(
            paste_window,
            text="Paste barcodes (format: barcode|barcode_out|item_name):",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(10, 5), padx=10)

        text_box = ctk.CTkTextbox(paste_window, height=250)
        text_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def parse_and_import():
            try:
                self.import_data = []
                lines = text_box.get("1.0", "end").strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) >= 3:
                        barcode = parts[0].strip()
                        barcode_out = parts[1].strip()
                        item_name = parts[2].strip()
                        if barcode and item_name:
                            self.import_data.append((barcode, barcode_out, item_name))

                if self.import_data:
                    self._show_preview()
                    paste_window.destroy()
                else:
                    messagebox.showwarning("No Data", "No valid barcodes found.")
            except Exception as e:
                messagebox.showerror("Error", f"Error parsing data: {str(e)}")

        ctk.CTkButton(
            paste_window, text="Import", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=parse_and_import,
        ).pack(side="right", padx=10, pady=10)

        ctk.CTkButton(
            paste_window, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=paste_window.destroy,
        ).pack(side="right", padx=(0, 10), pady=10)

    def _show_preview(self):
        """Show preview of imported data."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")

        preview_lines = []
        for barcode, barcode_out, item_name in self.import_data:
            preview_lines.append(f"{barcode} | {barcode_out} | {item_name}")

        self.preview_text.insert("1.0", "\n".join(preview_lines))
        self.preview_text.configure(state="disabled")

        self.status_lbl.configure(
            text=f"Ready to import {len(self.import_data)} barcode(s)",
            text_color="#27ae60"
        )

    def _import_data(self):
        """Import the data into the database."""
        if not self.import_data:
            self.status_lbl.configure(text="No data to import")
            return

        try:
            added = 0
            updated = 0
            errors = []

            for barcode, barcode_out, item_name in self.import_data:
                try:
                    # Check if barcode already exists
                    existing = self.db.get_item_by_barcode(barcode)
                    if existing:
                        # Update existing item
                        conn = self.db._connect()
                        conn.execute(
                            "UPDATE inventory_items SET barcode_out = ? WHERE barcode = ?",
                            (barcode_out, barcode)
                        )
                        conn.commit()
                        conn.close()
                        updated += 1
                    else:
                        # Create new item with barcode
                        ok, msg = self.db.add_item(
                            barcode=barcode,
                            item_name=item_name,
                            category="",
                            quantity=0,
                            min_stock=0,
                            notes="",
                            barcode_out=barcode_out
                        )
                        if ok:
                            added += 1
                        else:
                            errors.append(f"{barcode}: {msg}")
                except Exception as e:
                    errors.append(f"{barcode}: {str(e)}")

            message = f"Imported: {added} new, {updated} updated"
            if errors:
                message += f"\nErrors: {len(errors)}"
                for error in errors[:5]:  # Show first 5 errors
                    message += f"\n  - {error}"

            messagebox.showinfo("Import Complete", message)
            if self.on_complete:
                self.on_complete()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {str(e)}")
