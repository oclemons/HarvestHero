"""interactive_pantry_ui.py — Real-time interactive pantry UI with live updates.

Provides a fully interactive virtual pantry with:
- Live item cards with quantity controls
- Item detail drawer with threshold configuration
- Real-time quantity updates
- Filtering and search
- Inventory summary dashboard
- Shelf-level views
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import threading
from typing import Optional, Callable

from interactive_pantry import InteractivePantry
from theme import (
    BG_PRIMARY, BG_SURFACE, BG_ELEVATED, BG_HOVER, BG_OVERLAY,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)


class ItemDetailDrawer(ctk.CTkToplevel):
    """Modal drawer for viewing and editing item details."""

    def __init__(self, parent, item: dict, pantry: InteractivePantry, user: dict,
                 on_update: Optional[Callable] = None):
        super().__init__(parent)
        self.item = item
        self.pantry = pantry
        self.user = user
        self.on_update = on_update
        self.status = pantry.get_item_status(item)

        self.title(f"Item Details: {item.get('item_name', 'Unknown')}")
        self.geometry("500x700")
        self.resizable(False, False)

        self._build()
        self.grab_set()

    def _build(self):
        """Build the drawer UI."""
        main = ctk.CTkFrame(self, fg_color=BG_SURFACE)
        main.pack(fill="both", expand=True, padx=0, pady=0)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(main, fg_color=BG_ELEVATED, height=60)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text=self.item.get("item_name", "Unknown"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=16, pady=12)

        # Content
        content = ctk.CTkScrollableFrame(main, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        # Location info
        self._add_section(content, "Location")
        section, shelf = self.pantry._parse_location(self.item.get("storage_location", ""))
        ctk.CTkLabel(
            content, text=f"Section {section}, Shelf {shelf}" if section > 0 else "Not assigned",
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=12, pady=4)

        # Quantity section
        self._add_section(content, "Current Inventory")
        qty_frame = ctk.CTkFrame(content, fg_color="transparent")
        qty_frame.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            qty_frame, text=f"Quantity: {self.status.quantity} units",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        status_color = self._get_status_color()
        ctk.CTkLabel(
            qty_frame, text=self.status.status.upper(),
            text_color=status_color,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        ).pack(side="right")

        # Quantity controls (staff/admin only)
        if self.user.get("role") in ("admin", "staff"):
            ctrl_frame = ctk.CTkFrame(content, fg_color=BG_ELEVATED, corner_radius=8)
            ctrl_frame.pack(fill="x", padx=12, pady=8)
            ctrl_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                ctrl_frame, text="Adjust Quantity:",
                text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=10),
            ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(8, 4))

            self.qty_input = ctk.CTkEntry(
                ctrl_frame, placeholder_text="Amount", width=80, height=32,
            )
            self.qty_input.grid(row=1, column=0, padx=4, pady=4)

            ctk.CTkButton(
                ctrl_frame, text="+ Add", width=60, height=32,
                fg_color=ACCENT_GREEN, hover_color="#16a34a",
                text_color="white", corner_radius=6,
                command=self._add_quantity,
            ).grid(row=1, column=1, padx=4, pady=4)

            ctk.CTkButton(
                ctrl_frame, text="- Remove", width=70, height=32,
                fg_color=ACCENT_RED, hover_color="#dc2626",
                text_color="white", corner_radius=6,
                command=self._remove_quantity,
            ).grid(row=1, column=2, padx=4, pady=4)

        # Thresholds section (admin only)
        if self.user.get("role") == "admin":
            self._add_section(content, "Thresholds")

            # Low-stock threshold
            ctk.CTkLabel(
                content, text="Low-Stock Threshold:",
                text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=10),
            ).pack(anchor="w", padx=12, pady=(8, 2))

            self.low_input = ctk.CTkEntry(
                content, placeholder_text="Minimum quantity before low-stock alert",
                height=32,
            )
            self.low_input.pack(fill="x", padx=12, pady=4)
            self.low_input.insert(0, str(self.status.low_threshold))

            # Overstock threshold
            ctk.CTkLabel(
                content, text="Overstock Threshold:",
                text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=10),
            ).pack(anchor="w", padx=12, pady=(8, 2))

            self.over_input = ctk.CTkEntry(
                content, placeholder_text="Maximum quantity before overstock alert",
                height=32,
            )
            self.over_input.pack(fill="x", padx=12, pady=4)
            self.over_input.insert(0, str(self.status.overstock_threshold))

            ctk.CTkButton(
                content, text="Save Thresholds", height=36,
                fg_color=ACCENT_BLUE, hover_color="#1d4ed8",
                text_color="white", corner_radius=8,
                command=self._save_thresholds,
            ).pack(fill="x", padx=12, pady=8)

        # Item details
        self._add_section(content, "Item Details")
        self._add_detail_row(content, "Barcode", self.item.get("barcode", "N/A"))
        self._add_detail_row(content, "Brand", self.item.get("brand", "N/A"))
        self._add_detail_row(content, "Category", self.item.get("category", "N/A"))
        self._add_detail_row(content, "Expires", self.item.get("expiration_date", "N/A"))

        # Footer
        footer = ctk.CTkFrame(main, fg_color=BG_ELEVATED, height=50)
        footer.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer.pack_propagate(False)

        ctk.CTkButton(
            footer, text="Close", width=100, height=36,
            fg_color=BG_SURFACE, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self.destroy,
        ).pack(side="right", padx=12, pady=7)

    def _add_section(self, parent, title: str):
        """Add a section header."""
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=12, pady=(12, 4))

    def _add_detail_row(self, parent, label: str, value: str):
        """Add a detail row."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=2)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text=f"{label}:",
            text_color=TEXT_MUTED, font=ctk.CTkFont(size=10),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            frame, text=value,
            text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=10),
        ).grid(row=0, column=1, sticky="e")

    def _get_status_color(self) -> str:
        """Get color for current status."""
        status_colors = {
            "low": "#fcd34d",
            "normal": "#86efac",
            "overstock": "#a78bfa",
            "not_configured": "#9ca3af",
        }
        return status_colors.get(self.status.status, TEXT_SECONDARY)

    def _add_quantity(self):
        """Add quantity."""
        try:
            amount = int(self.qty_input.get())
            if amount <= 0:
                messagebox.showerror("Invalid", "Amount must be positive")
                return

            success, msg, new_qty = self.pantry.update_quantity(
                self.item["id"], amount, self.user
            )
            if success:
                self.item["current_quantity"] = new_qty
                self.status = self.pantry.get_item_status(self.item)
                self.qty_input.delete(0, "end")
                messagebox.showinfo("Success", msg)
                if self.on_update:
                    self.on_update()
            else:
                messagebox.showerror("Error", msg)
        except ValueError:
            messagebox.showerror("Invalid", "Please enter a valid number")

    def _remove_quantity(self):
        """Remove quantity."""
        try:
            amount = int(self.qty_input.get())
            if amount <= 0:
                messagebox.showerror("Invalid", "Amount must be positive")
                return

            success, msg, new_qty = self.pantry.update_quantity(
                self.item["id"], -amount, self.user
            )
            if success:
                self.item["current_quantity"] = new_qty
                self.status = self.pantry.get_item_status(self.item)
                self.qty_input.delete(0, "end")
                messagebox.showinfo("Success", msg)
                if self.on_update:
                    self.on_update()
            else:
                messagebox.showerror("Error", msg)
        except ValueError:
            messagebox.showerror("Invalid", "Please enter a valid number")

    def _save_thresholds(self):
        """Save threshold changes."""
        try:
            low = int(self.low_input.get())
            over = int(self.over_input.get())

            success, msg = self.pantry.update_thresholds(
                self.item["id"], low, over, self.user
            )
            if success:
                messagebox.showinfo("Success", msg)
                if self.on_update:
                    self.on_update()
            else:
                messagebox.showerror("Error", msg)
        except ValueError:
            messagebox.showerror("Invalid", "Please enter valid numbers")


class InteractivePantryUI(ctk.CTkFrame):
    """Main interactive pantry UI."""

    def __init__(self, parent, db, user: dict, **kwargs):
        super().__init__(parent, fg_color=BG_PRIMARY, **kwargs)
        self.db = db
        self.user = user
        self.pantry = InteractivePantry(db)
        self._current_filter = None
        self._current_search = ""
        self._items = []

        self._build()
        self.load_pantry()

    def _build(self):
        """Build the UI."""
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Interactive Pantry",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=(0, 20))

        # Search
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        ctk.CTkEntry(
            header, textvariable=self.search_var, width=300, height=36,
            placeholder_text="Search items...",
            fg_color=BG_SURFACE, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            header, text="↻ Refresh", width=90, height=36,
            fg_color=BG_SURFACE, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self.load_pantry,
        ).grid(row=0, column=2, sticky="e")

        # Summary cards
        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        summary_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.summary_labels = {}
        for idx, (key, label, color) in enumerate([
            ("total_items", "Total Items", TEXT_PRIMARY),
            ("normal_items", "Normal", ACCENT_GREEN),
            ("low_stock_items", "Low Stock", ACCENT_AMBER),
            ("overstock_items", "Overstock", ACCENT_BLUE),
            ("not_configured", "Not Configured", TEXT_MUTED),
        ]):
            card = self._create_summary_card(summary_frame, label, color, key)
            card.grid(row=0, column=idx, sticky="ew", padx=4)
            self.summary_labels[key] = card

        # Content
        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content_frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 12))
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _create_summary_card(self, parent, label: str, color: str, key: str) -> ctk.CTkFrame:
        """Create a summary statistic card."""
        card = ctk.CTkFrame(
            parent, fg_color=BG_ELEVATED, corner_radius=8,
            border_width=1, border_color=BORDER_COLOR,
        )

        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).pack(padx=12, pady=(8, 2))

        self.summary_value_labels = getattr(self, 'summary_value_labels', {})
        value_label = ctk.CTkLabel(
            card, text="0",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=color,
        )
        value_label.pack(padx=12, pady=(2, 8))
        self.summary_value_labels[key] = value_label

        return card

    def load_pantry(self):
        """Load pantry data."""
        def load():
            try:
                self._items = self.db.get_all_items()
                self.after(0, self._populate_pantry)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load: {e}"))

        threading.Thread(target=load, daemon=True).start()

    def _populate_pantry(self):
        """Populate the pantry view."""
        # Clear
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Update summary
        summary = self.pantry.get_pantry_summary()
        if not hasattr(self, 'summary_value_labels'):
            self.summary_value_labels = {}

        for key, label in [
            ("total_items", "Total Items"),
            ("normal_items", "Normal"),
            ("low_stock_items", "Low Stock"),
            ("overstock_items", "Overstock"),
            ("not_configured", "Not Configured"),
        ]:
            if key in self.summary_value_labels:
                self.summary_value_labels[key].configure(text=str(summary.get(key, 0)))

        # Organize by section
        sections = {}
        for item in self._items:
            section, shelf = self.pantry._parse_location(item.get("storage_location", ""))
            if section not in sections:
                sections[section] = {}
            if shelf not in sections[section]:
                sections[section][shelf] = []
            sections[section][shelf].append(item)

        # Display sections
        for section_num in sorted(sections.keys()):
            self._create_section_view(self.content_frame, section_num, sections[section_num])

    def _create_section_view(self, parent, section_num: int, shelves: dict):
        """Create a section view."""
        section_frame = ctk.CTkFrame(parent, fg_color=BG_SURFACE, corner_radius=8)
        section_frame.pack(fill="x", padx=0, pady=8)
        section_frame.grid_columnconfigure(0, weight=1)

        title = f"Section {section_num}" if section_num > 0 else "Unorganized"
        ctk.CTkLabel(
            section_frame, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        # Shelves
        for idx, shelf_num in enumerate(sorted(shelves.keys()), start=1):
            items = shelves[shelf_num]
            self._create_shelf_view(section_frame, shelf_num, items, idx)

    def _create_shelf_view(self, parent, shelf_num: int, items: list, row: int):
        """Create a shelf view."""
        shelf_frame = ctk.CTkFrame(parent, fg_color=BG_ELEVATED, corner_radius=6)
        shelf_frame.grid(row=row, column=0, sticky="ew", padx=12, pady=4)
        shelf_frame.grid_columnconfigure(0, weight=1)

        # Shelf header
        header = ctk.CTkFrame(shelf_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text=f"Shelf {shelf_num}" if shelf_num > 0 else "Unassigned",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header, text=f"{len(items)} items",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=1, sticky="e")

        # Items
        items_frame = ctk.CTkFrame(shelf_frame, fg_color="transparent")
        items_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        items_frame.grid_columnconfigure((0, 1), weight=1)

        for idx, item in enumerate(items):
            col = idx % 2
            row_idx = idx // 2
            self._create_item_card(items_frame, item, col, row_idx)

    def _create_item_card(self, parent, item: dict, col: int, row: int):
        """Create an interactive item card."""
        status = self.pantry.get_item_status(item)
        color = self._get_status_color(status.status)

        card = ctk.CTkButton(
            parent,
            text=f"{item.get('item_name', 'Unknown')}\n{status.quantity} units\n{status.status.upper()}",
            fg_color=color, hover_color=color,
            text_color="black" if color in ("#fcd34d", "#86efac") else "white",
            corner_radius=6, height=80,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: self._open_item_details(item),
        )
        card.grid(row=row, column=col, sticky="ew", padx=4, pady=4)

    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        colors = {
            "low": "#fcd34d",
            "normal": "#86efac",
            "overstock": "#a78bfa",
            "not_configured": "#9ca3af",
        }
        return colors.get(status, TEXT_SECONDARY)

    def _open_item_details(self, item: dict):
        """Open item detail drawer."""
        ItemDetailDrawer(self, item, self.pantry, self.user, on_update=self.load_pantry)

    def _on_search(self, *args):
        """Handle search."""
        self._current_search = self.search_var.get().lower()
        self._apply_filters()

    def _apply_filters(self):
        """Apply search and status filters."""
        filtered = self._items

        # Search filter
        if self._current_search:
            filtered = [
                item for item in filtered
                if self._current_search in item.get("item_name", "").lower() or
                   self._current_search in item.get("barcode", "").lower()
            ]

        # Rebuild with filtered items
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        sections = {}
        for item in filtered:
            section, shelf = self.pantry._parse_location(item.get("storage_location", ""))
            if section not in sections:
                sections[section] = {}
            if shelf not in sections[section]:
                sections[section][shelf] = []
            sections[section][shelf].append(item)

        for section_num in sorted(sections.keys()):
            self._create_section_view(self.content_frame, section_num, sections[section_num])

    def on_shown(self):
        """Called when view becomes visible."""
        self.load_pantry()
