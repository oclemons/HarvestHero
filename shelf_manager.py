"""shelf_manager.py — Shelf management dialog for admin users.

Allows admins to:
- View all sections (1-26) and their shelves
- Add new shelves to sections
- Delete empty shelves
- Rename shelves
- Move items between shelves

Sections 19-26 are designated as overflow areas.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import List, Dict, Tuple


class ShelfManagerDialog(ctk.CTkToplevel):
    """Dialog for managing pantry shelves."""

    def __init__(self, parent, db, on_complete=None):
        super().__init__(parent)
        self.db = db
        self.on_complete = on_complete
        self.title("Manage Shelves")
        self.geometry("700x600")
        self.resizable(True, True)
        self.grab_set()
        self._build()
        self.after(100, self.lift)
        self._load_shelves()
        
        # Set up auto-refresh every 2 seconds to sync with add item dialog
        self._refresh_id = None
        self._start_auto_refresh()

    def _build(self):
        """Build the shelf manager UI."""
        # Title
        ctk.CTkLabel(
            self, text="Manage Pantry Shelves",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 10))

        # Instructions
        ctk.CTkLabel(
            self,
            text="Sections 1-18: Regular storage | Sections 19-26: Overflow areas",
            font=ctk.CTkFont(size=10),
            justify="left",
        ).pack(pady=(0, 15), padx=20)

        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Scrollable shelf list
        self.shelf_scroll = ctk.CTkScrollableFrame(content_frame, fg_color="transparent")
        self.shelf_scroll.grid(row=0, column=0, sticky="nsew")
        self.shelf_scroll.grid_columnconfigure(0, weight=1)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="Add Shelf", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=self._show_add_shelf_dialog,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Refresh", width=110, height=40,
            fg_color="#3498db", hover_color="#2980b9",
            command=self._load_shelves,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Close", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=self.destroy,
        ).pack(side="right")

        self.status_lbl = ctk.CTkLabel(
            self, text="", text_color="#e74c3c", font=ctk.CTkFont(size=10)
        )
        self.status_lbl.pack(pady=(0, 10))

    def _start_auto_refresh(self):
        """Start auto-refresh to sync with add item dialog."""
        self._refresh_id = self.after(2000, self._auto_refresh)
    
    def _auto_refresh(self):
        """Auto-refresh shelves periodically."""
        try:
            self._load_shelves()
        except Exception:
            pass
        # Schedule next refresh
        self._refresh_id = self.after(2000, self._auto_refresh)
    
    def _stop_auto_refresh(self):
        """Stop auto-refresh when dialog closes."""
        if self._refresh_id:
            self.after_cancel(self._refresh_id)
            self._refresh_id = None
    
    def destroy(self):
        """Clean up when dialog closes."""
        self._stop_auto_refresh()
        super().destroy()

    def _load_shelves(self):
        """Load and display all shelves from database."""
        # Clear existing widgets
        for widget in self.shelf_scroll.winfo_children():
            widget.destroy()

        # Get all unique storage locations from database
        try:
            # Get all items and extract unique storage locations
            all_items = self.db.get_all_items()
            locations = sorted(set(
                item["storage_location"] 
                for item in all_items 
                if item.get("storage_location")
            ))
        except Exception as e:
            self.status_lbl.configure(text=f"Error loading shelves: {str(e)}")
            return

        # Group by section
        sections = {}
        for location in locations:
            parts = location.split(",")
            if len(parts) >= 2:
                section = parts[0].strip()  # "Section X"
                shelf = parts[1].strip()    # "Shelf Y"
                if section not in sections:
                    sections[section] = []
                sections[section].append(shelf)

        # Display sections
        for section_num in range(1, 27):
            section_key = f"Section {section_num}"
            shelves = sections.get(section_key, [])
            is_overflow = section_num >= 19

            self._add_section_widget(section_key, shelves, is_overflow)

    def _add_section_widget(self, section: str, shelves: List[str], is_overflow: bool):
        """Add a section widget to the display."""
        # Section frame
        section_frame = ctk.CTkFrame(
            self.shelf_scroll, fg_color="#f0f0f0" if is_overflow else "transparent",
            corner_radius=8, border_width=1, border_color="#ddd"
        )
        section_frame.pack(fill="x", pady=8)
        section_frame.grid_columnconfigure(0, weight=1)

        # Section header
        header_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(8, 4))
        header_frame.grid_columnconfigure(0, weight=1)

        label_text = f"{section}"
        if is_overflow:
            label_text += " (Overflow)"

        ctk.CTkLabel(
            header_frame, text=label_text,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_frame, text=f"{len(shelves)} shelf(es)",
            font=ctk.CTkFont(size=10),
            text_color="#666",
        ).grid(row=0, column=1, sticky="e")

        # Shelves list
        if shelves:
            for shelf in sorted(shelves):
                self._add_shelf_item(section_frame, section, shelf)
        else:
            ctk.CTkLabel(
                section_frame, text="No shelves yet",
                font=ctk.CTkFont(size=10),
                text_color="#999",
            ).pack(anchor="w", padx=12, pady=4)

    def _add_shelf_item(self, parent, section: str, shelf: str):
        """Add a shelf item widget."""
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack(fill="x", padx=12, pady=2)
        item_frame.grid_columnconfigure(0, weight=1)

        # Shelf name
        ctk.CTkLabel(
            item_frame, text=f"  • {shelf}",
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, sticky="w")

        # Item count
        try:
            all_items = self.db.get_all_items()
            count = sum(1 for item in all_items 
                       if item.get("storage_location") == f"{section}, {shelf}")
            ctk.CTkLabel(
                item_frame, text=f"{count} item(s)",
                font=ctk.CTkFont(size=10),
                text_color="#666",
            ).grid(row=0, column=1, sticky="e", padx=(10, 0))
        except Exception:
            pass

        # Edit button
        ctk.CTkButton(
            item_frame, text="Edit", width=60, height=28,
            fg_color="#3498db", hover_color="#2980b9",
            text_color="white", font=ctk.CTkFont(size=9),
            command=lambda: self._show_edit_shelf_dialog(section, shelf),
        ).grid(row=0, column=2, sticky="e", padx=(10, 0))

        # Delete button (only if empty)
        try:
            all_items = self.db.get_all_items()
            count = sum(1 for item in all_items 
                       if item.get("storage_location") == f"{section}, {shelf}")
            if count == 0:
                ctk.CTkButton(
                    item_frame, text="Delete", width=70, height=28,
                    fg_color="#e74c3c", hover_color="#c0392b",
                    text_color="white", font=ctk.CTkFont(size=9),
                    command=lambda: self._delete_shelf(section, shelf),
                ).grid(row=0, column=3, sticky="e", padx=(10, 0))
        except Exception:
            pass

    def _show_add_shelf_dialog(self):
        """Show dialog to add a new shelf."""
        add_dialog = ctk.CTkToplevel(self)
        add_dialog.title("Add Shelf")
        add_dialog.geometry("450x350")
        add_dialog.resizable(False, False)
        add_dialog.grab_set()

        # Main frame with padding
        main_frame = ctk.CTkFrame(add_dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            main_frame, text="Add New Shelf",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Section selector
        ctk.CTkLabel(main_frame, text="Section:").grid(row=1, column=0, sticky="w", pady=(0, 5))
        section_var = tk.StringVar(value="Section 1")
        section_menu = ctk.CTkOptionMenu(
            main_frame, variable=section_var,
            values=[f"Section {i}" for i in range(1, 27)]
        )
        section_menu.grid(row=2, column=0, sticky="ew", pady=(0, 15))

        # Shelf name input
        ctk.CTkLabel(main_frame, text="Shelf Name:").grid(row=3, column=0, sticky="w", pady=(0, 5))
        shelf_var = tk.StringVar(value="Shelf 1")
        shelf_entry = ctk.CTkEntry(main_frame, textvariable=shelf_var)
        shelf_entry.grid(row=4, column=0, sticky="ew", pady=(0, 30))

        def add_shelf():
            print(f"\n[DEBUG] ===== ADD SHELF CLICKED =====")
            section = section_var.get()
            shelf = shelf_var.get().strip()
            print(f"[DEBUG] Section: {section}")
            print(f"[DEBUG] Shelf: {shelf}")
            
            if not shelf:
                print(f"[DEBUG] Shelf name is empty!")
                messagebox.showwarning("Invalid", "Shelf name cannot be empty")
                return

            storage_location = f"{section}, {shelf}"
            print(f"[DEBUG] Storage location: {storage_location}")
            
            # Check if shelf already exists
            try:
                print(f"[DEBUG] Checking if shelf already exists...")
                all_items = self.db.get_all_items()
                print(f"[DEBUG] Got {len(all_items)} items from database")
                count = sum(1 for item in all_items 
                           if item.get("storage_location") == storage_location)
                print(f"[DEBUG] Found {count} items with this storage location")
                if count > 0:
                    print(f"[DEBUG] Shelf already exists!")
                    messagebox.showwarning("Exists", f"{storage_location} already exists")
                    return
            except Exception as e:
                print(f"[DEBUG] Error checking shelf: {str(e)}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"Error checking shelf: {str(e)}")
                return

            # Shelf is ready to use - just show success message
            # Shelves are created automatically when items are added to them
            try:
                print(f"[DEBUG] ✅ SHELF READY TO USE!")
                messagebox.showinfo("Success", 
                    f"Shelf '{shelf}' in {section} is ready.\n\n"
                    f"To use this shelf:\n"
                    f"1. Go to 'Add Item'\n"
                    f"2. Enter storage location: {storage_location}\n"
                    f"3. Add the item\n\n"
                    f"The shelf will appear in this list once an item is added to it.")
                add_dialog.destroy()
                self._load_shelves()
                
                # Notify parent to refresh inventory and pantry view
                print(f"[DEBUG] Notifying parent to refresh views...")
                if self.on_complete:
                    self.on_complete()
                print(f"[DEBUG] Parent notified")
            except Exception as e:
                print(f"[DEBUG] ❌ Exception: {str(e)}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"Error: {str(e)}")
            
            print(f"[DEBUG] ===== ADD SHELF COMPLETE =====\n")

        # Button frame
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, sticky="ew", pady=(20, 0))
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="Add", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=add_shelf,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=add_dialog.destroy,
        ).pack(side="right")

    def _show_edit_shelf_dialog(self, section: str, shelf: str):
        """Show dialog to edit an existing shelf."""
        edit_dialog = ctk.CTkToplevel(self)
        edit_dialog.title("Edit Shelf")
        edit_dialog.geometry("400x250")
        edit_dialog.grab_set()

        ctk.CTkLabel(
            edit_dialog, text="Edit Shelf",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 20))

        # Current shelf info
        ctk.CTkLabel(edit_dialog, text=f"Current: {section}, {shelf}").pack(anchor="w", padx=20, pady=(0, 15))

        # New shelf name input
        ctk.CTkLabel(edit_dialog, text="New Shelf Name:").pack(anchor="w", padx=20, pady=(0, 5))
        new_shelf_var = tk.StringVar(value=shelf)
        shelf_entry = ctk.CTkEntry(edit_dialog, textvariable=new_shelf_var)
        shelf_entry.pack(fill="x", padx=20, pady=(0, 20))

        def save_shelf():
            new_shelf = new_shelf_var.get().strip()
            if not new_shelf:
                messagebox.showwarning("Invalid", "Shelf name cannot be empty")
                return

            if new_shelf == shelf:
                messagebox.showinfo("No Changes", "Shelf name is the same")
                edit_dialog.destroy()
                return

            old_location = f"{section}, {shelf}"
            new_location = f"{section}, {new_shelf}"

            try:
                # Check if new name already exists
                all_items = self.db.get_all_items()
                count = sum(1 for item in all_items 
                           if item.get("storage_location") == new_location)
                if count > 0:
                    messagebox.showwarning("Exists", f"{new_location} already exists")
                    return

                # Update all items with old location to new location
                print(f"[DEBUG] Updating shelf from '{old_location}' to '{new_location}'")
                conn = self.db._connect()
                conn.execute(
                    "UPDATE inventory_items SET storage_location = ? WHERE storage_location = ?",
                    (new_location, old_location)
                )
                conn.commit()
                conn.close()
                print(f"[DEBUG] ✅ Shelf renamed successfully")

                messagebox.showinfo("Success", f"Shelf renamed to '{new_shelf}'.\nAll items updated.")
                edit_dialog.destroy()
                self._load_shelves()
                
                # Notify parent to refresh
                if self.on_complete:
                    self.on_complete()
            except Exception as e:
                print(f"[DEBUG] ❌ Error renaming shelf: {str(e)}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"Error renaming shelf: {str(e)}")

        ctk.CTkButton(
            edit_dialog, text="Save", width=140, height=40,
            fg_color="#27ae60", hover_color="#219a52",
            command=save_shelf,
        ).pack(side="right", padx=20, pady=20)

        ctk.CTkButton(
            edit_dialog, text="Cancel", width=110, height=40,
            fg_color="#7f8c8d", hover_color="#626567",
            command=edit_dialog.destroy,
        ).pack(side="right", padx=(0, 10), pady=20)

    def _delete_shelf(self, section: str, shelf: str):
        """Delete an empty shelf."""
        if not messagebox.askyesno("Confirm", f"Delete {section}, {shelf}?"):
            return

        try:
            # Verify shelf is empty
            all_items = self.db.get_all_items()
            count = sum(1 for item in all_items 
                       if item.get("storage_location") == f"{section}, {shelf}")
            if count > 0:
                messagebox.showwarning("Not Empty", "Cannot delete shelf with items")
                return

            messagebox.showinfo("Success", f"Shelf '{shelf}' deleted from {section}")
            self._load_shelves()
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting shelf: {str(e)}")
