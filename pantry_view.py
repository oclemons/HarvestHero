"""pantry_view.py — Virtual pantry grid visualization.

Displays inventory as a visual grid of sections and shelves, making it
easy to see what's where and identify overstock situations.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import threading

from pantry_organizer import PantryOrganizer
from theme import (
    BG_PRIMARY, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)


class ShelfCard(ctk.CTkFrame):
    """Visual card representing a shelf with items."""

    def __init__(self, parent, section_num: int, shelf_num: int,
                 items: list, organizer: PantryOrganizer, on_item_click=None, **kwargs):
        super().__init__(parent, fg_color=BG_ELEVATED, corner_radius=8,
                        border_width=1, border_color=BORDER_COLOR, **kwargs)
        self.section_num = section_num
        self.shelf_num = shelf_num
        self.items = items
        self.organizer = organizer
        self.on_item_click = on_item_click

        self._build()

    def _build(self):
        """Build the shelf card UI."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        header.grid_columnconfigure(0, weight=1)

        section_label = f"Section {self.section_num}" if self.section_num > 0 else "Unorganized"
        shelf_label = f"Shelf {self.shelf_num}" if self.shelf_num > 0 else ""

        ctk.CTkLabel(
            header, text=f"{section_label} {shelf_label}".strip(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", anchor="w")

        # Item count and capacity
        total_units, overstock_count = self.organizer.get_shelf_capacity(self.items)
        capacity_text = f"{len(self.items)} items, {total_units} units"
        if overstock_count > 0:
            capacity_text += f" ({overstock_count} overstock)"

        ctk.CTkLabel(
            header, text=capacity_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED,
        ).pack(side="right", anchor="e")

        # Items container
        items_frame = ctk.CTkFrame(self, fg_color="transparent")
        items_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        items_frame.grid_columnconfigure(0, weight=1)

        if not self.items:
            ctk.CTkLabel(
                items_frame, text="(empty)",
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=TEXT_MUTED,
            ).pack(padx=4, pady=4)
        else:
            for item in self.items:
                self._create_item_button(items_frame, item)

    def _create_item_button(self, parent, item: dict):
        """Create a button for an item."""
        status, color = self.organizer.get_item_status(item)
        qty = item.get("current_quantity", 0)
        name = item.get("item_name", "Unknown")

        # Truncate name if too long
        if len(name) > 25:
            name = name[:22] + "..."

        btn = ctk.CTkButton(
            parent,
            text=f"{name}\n{qty} units",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            fg_color=color, hover_color=color,
            text_color="black" if color in ("#fcd34d", "#fbbf24", "#a78bfa", "#86efac") else "white",
            corner_radius=6,
            height=50,
            command=lambda: self._on_click(item),
        )
        btn.pack(fill="x", padx=2, pady=2)

    def _on_click(self, item: dict):
        """Handle item click."""
        if self.on_item_click:
            self.on_item_click(item)


class SectionView(ctk.CTkFrame):
    """View for a single section with multiple shelves."""

    def __init__(self, parent, section_num: int, section, organizer: PantryOrganizer,
                 on_item_click=None, **kwargs):
        super().__init__(parent, fg_color=BG_SURFACE, corner_radius=8, **kwargs)
        self.section_num = section_num
        self.section = section
        self.organizer = organizer
        self.on_item_click = on_item_click

        self._build()

    def _build(self):
        """Build the section view."""
        self.grid_columnconfigure(0, weight=1)

        # Section title
        title = f"Section {self.section_num}" if self.section_num > 0 else "Unorganized Items"
        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        # Shelves grid
        shelves_frame = ctk.CTkFrame(self, fg_color="transparent")
        shelves_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        shelves_frame.grid_columnconfigure(0, weight=1)

        for idx, shelf_num in enumerate(self.section.get_shelves()):
            items = self.section.get_items_on_shelf(shelf_num)
            ShelfCard(
                shelves_frame,
                self.section_num, shelf_num, items,
                self.organizer,
                on_item_click=self.on_item_click,
            ).grid(row=idx, column=0, sticky="ew", pady=4)


class PantryView(ctk.CTkFrame):
    """Virtual pantry grid view showing all sections and shelves."""

    def __init__(self, parent, db, user: dict, on_item_click=None, **kwargs):
        super().__init__(parent, fg_color=BG_PRIMARY, **kwargs)
        self.db = db
        self.user = user
        self.on_item_click = on_item_click
        self.organizer = PantryOrganizer(db)
        self._sections_frame = None
        self._load_thread = None

        self._build()
        self.load_pantry()

    def _build(self):
        """Build the UI layout."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Virtual Pantry",
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

        # Stats bar
        self.stats_label = ctk.CTkLabel(
            self, text="Loading...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.stats_label.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 12))
        scroll.grid_columnconfigure(0, weight=1)

        self._sections_frame = scroll

    def load_pantry(self):
        """Load pantry data in background."""
        def load():
            try:
                items = self.db.get_all_items()
                self.organizer.organize(items)
                self.after(0, self._populate_pantry)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to load pantry: {e}"))

        self._load_thread = threading.Thread(target=load, daemon=True)
        self._load_thread.start()

    def _populate_pantry(self):
        """Populate the pantry view with sections."""
        # Clear existing
        for widget in self._sections_frame.winfo_children():
            widget.destroy()

        sections = self.organizer.get_sections()
        if not sections:
            ctk.CTkLabel(
                self._sections_frame, text="No items in inventory",
                text_color=TEXT_MUTED,
            ).pack(padx=12, pady=12)
            self.stats_label.configure(text="No items")
            return

        # Populate sections
        for section_num in sections:
            section = self.organizer.get_section(section_num)
            SectionView(
                self._sections_frame,
                section_num, section,
                self.organizer,
                on_item_click=self.on_item_click,
            ).pack(fill="x", padx=0, pady=8)

        # Update stats
        stats = self.organizer.get_pantry_stats()
        stats_text = (
            f"{stats['total_items']} items ({stats['total_units']} units) • "
            f"{stats['sections']} sections • "
            f"⚠ {stats['overstock_items']} overstock • "
            f"🔴 {stats['out_of_stock']} out of stock • "
            f"🟡 {stats['low_stock']} low stock"
        )
        self.stats_label.configure(text=stats_text)

    def _on_search(self, *args):
        """Handle search filter."""
        query = self.search_var.get().lower()

        # Show/hide sections and shelves based on search
        for section_widget in self._sections_frame.winfo_children():
            if not isinstance(section_widget, SectionView):
                continue

            section_visible = False
            for shelf_widget in section_widget.winfo_children():
                if not isinstance(shelf_widget, ShelfCard):
                    continue

                shelf_visible = False
                for item_btn in shelf_widget.winfo_children():
                    if isinstance(item_btn, ctk.CTkButton):
                        # Check if item matches search
                        for item in shelf_widget.items:
                            if query in item.get("item_name", "").lower() or \
                               query in item.get("barcode", "").lower():
                                item_btn.pack(fill="x", padx=2, pady=2)
                                shelf_visible = True
                                section_visible = True
                            else:
                                item_btn.pack_forget()

                if shelf_visible:
                    shelf_widget.pack(fill="x", padx=0, pady=4)
                else:
                    shelf_widget.pack_forget()

            if section_visible:
                section_widget.pack(fill="x", padx=0, pady=8)
            else:
                section_widget.pack_forget()

    def on_shown(self):
        """Called when view becomes visible."""
        self.load_pantry()
