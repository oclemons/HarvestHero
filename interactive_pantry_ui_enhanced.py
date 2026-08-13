"""
interactive_pantry_ui_enhanced.py — Premium visual pantry interface.

Provides a graphical shelf visualization with:
- Visual shelf structure
- Item cards with status indicators
- Interactive elements
- Search and filtering
- Glass effects throughout
"""

import customtkinter as ctk
from typing import Callable, Optional, List
from glass_effects_premium import GlassEffectManager
from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
)


class PantryItemCard(ctk.CTkFrame):
    """Visual item card for pantry display."""

    def __init__(self, parent, item: dict, on_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color=BG_ELEVATED, corner_radius=12,
                         border_width=1, border_color=BORDER_SUBTLE, **kwargs)
        self.item = item
        self.on_click = on_click
        self._build(item)
        self.bind("<Button-1>", lambda e: on_click(item) if on_click else None)
        for w in self.winfo_children():
            w.bind("<Button-1>", lambda e: on_click(item) if on_click else None)

    def _build(self, item: dict):
        """Build the item card layout."""
        # Header with item name and status
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 8))

        # Item name
        ctk.CTkLabel(
            header, text=item.get("item_name", "Unknown"),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", side="left", fill="x", expand=True)

        # Status indicator
        status = self._get_status(item)
        status_color = self._get_status_color(status)
        ctk.CTkLabel(
            header, text=status,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=status_color, fg_color="transparent"
        ).pack(anchor="e", side="right")

        # Quantity display
        qty_frame = ctk.CTkFrame(self, fg_color="transparent")
        qty_frame.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            qty_frame, text="Qty:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY, fg_color="transparent"
        ).pack(side="left")

        qty = item.get("current_quantity", 0)
        ctk.CTkLabel(
            qty_frame, text=str(qty),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(side="left", padx=(4, 0))

        # Thresholds
        low = item.get("minimum_stock", 0)
        over = item.get("overstock_threshold", 0)
        if low or over:
            threshold_text = f"Low: {low}" + (f" / Over: {over}" if over else "")
            ctk.CTkLabel(
                qty_frame, text=threshold_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=TEXT_MUTED, fg_color="transparent"
            ).pack(side="right")

    @staticmethod
    def _get_status(item: dict) -> str:
        """Determine item status."""
        qty = item.get("current_quantity", 0)
        low = item.get("minimum_stock", 0)
        over = item.get("overstock_threshold", 0)

        if qty == 0:
            return "OUT"
        elif qty <= low:
            return "LOW"
        elif over and qty > over:
            return "OVER"
        else:
            return "OK"

    @staticmethod
    def _get_status_color(status: str) -> str:
        """Get color for status."""
        if status == "OUT":
            return ACCENT_RED
        elif status == "LOW":
            return ACCENT_AMBER
        elif status == "OVER":
            return ACCENT_AMBER
        else:
            return ACCENT_GREEN


class PantryShelfView(ctk.CTkFrame):
    """Visual representation of a pantry shelf."""

    def __init__(self, parent, shelf_name: str, items: List[dict],
                 on_item_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.shelf_name = shelf_name
        self.items = items
        self.on_item_click = on_item_click
        self._build()

    def _build(self):
        """Build the shelf layout."""
        # Shelf header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(12, 8))

        ctk.CTkLabel(
            header, text=self.shelf_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", side="left")

        # Item count
        ctk.CTkLabel(
            header, text=f"{len(self.items)} items",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, fg_color="transparent"
        ).pack(anchor="e", side="right")

        # Shelf divider
        ctk.CTkFrame(self, fg_color=BORDER_SUBTLE, height=1).pack(fill="x", pady=(0, 12))

        # Items grid
        items_frame = ctk.CTkFrame(self, fg_color="transparent")
        items_frame.pack(fill="both", expand=True, padx=0, pady=(0, 16))

        if self.items:
            # Create a grid of item cards
            for i, item in enumerate(self.items):
                card = PantryItemCard(
                    items_frame, item,
                    on_click=self.on_item_click,
                    width=180, height=100
                )
                row = i // 4
                col = i % 4
                card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            # Configure grid weights
            for i in range(4):
                items_frame.grid_columnconfigure(i, weight=1)
        else:
            ctk.CTkLabel(
                items_frame, text="No items on this shelf",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED, fg_color="transparent"
            ).pack(pady=20)


class PantryVisualizerFrame(ctk.CTkFrame):
    """Main pantry visualizer with shelves and items."""

    def __init__(self, parent, db, on_item_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color=BG_BASE, **kwargs)
        self.db = db
        self.on_item_click = on_item_click
        self._glass_manager = GlassEffectManager({
            "name": "Harvest Day",
            "BG_ELEVATED": BG_ELEVATED,
            "BORDER_SUBTLE": BORDER_SUBTLE,
            "BORDER_COLOR": BORDER_COLOR,
            "TEXT_PRIMARY": TEXT_PRIMARY,
            "TEXT_SECONDARY": TEXT_SECONDARY,
        })
        self._build()

    def _build(self):
        """Build the main pantry visualizer."""
        # Header with title and controls
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            header, text="Virtual Pantry",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, fg_color="transparent"
        ).pack(anchor="w", side="left")

        # Search frame
        search_frame = ctk.CTkFrame(header, fg_color="transparent")
        search_frame.pack(anchor="e", side="right")

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search items...",
            width=200, height=32,
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11)
        )
        self.search_entry.pack(side="left", padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        # Refresh button
        ctk.CTkButton(
            search_frame, text="🔄 Refresh", width=100, height=32,
            fg_color=ACCENT, hover_color=ACCENT,
            text_color="white", font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self.refresh
        ).pack(side="left")

        # Scrollable content area
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG_BASE, label_text="Shelves",
            label_fg_color=BG_BASE, label_text_color=TEXT_PRIMARY,
            label_font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.refresh()

    def _on_search(self):
        """Handle search input."""
        search_term = self.search_entry.get().lower().strip()
        self.refresh(search_term)

    def refresh(self, search_term: str = ""):
        """Refresh the pantry display."""
        # Clear existing shelves
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Get all items
        try:
            items = self.db.get_all_items()
        except Exception:
            items = []

        # Filter by search term
        if search_term:
            items = [i for i in items if search_term in i.get("item_name", "").lower()]

        # Group by storage location (shelf)
        shelves = {}
        for item in items:
            shelf = item.get("storage_location", "Unassigned")
            if shelf not in shelves:
                shelves[shelf] = []
            shelves[shelf].append(item)

        # Display shelves
        if shelves:
            for shelf_name in sorted(shelves.keys()):
                shelf_view = PantryShelfView(
                    self.scrollable_frame,
                    shelf_name,
                    shelves[shelf_name],
                    on_item_click=self.on_item_click
                )
                shelf_view.pack(fill="x", padx=0, pady=(0, 16))
        else:
            ctk.CTkLabel(
                self.scrollable_frame,
                text="No items found" if search_term else "Pantry is empty",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED, fg_color="transparent"
            ).pack(pady=40)
