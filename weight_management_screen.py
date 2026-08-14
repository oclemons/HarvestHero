"""weight_management_screen.py — Weight management and tracking screen.

Allows admins to:
- View all items with their current weights
- Edit weights for individual items
- View weight history
- See monthly summaries
"""

import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
from weight_entry_dialog import WeightEntryDialog

from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER, BG_ELEVATED,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
)


def _apply_treeview_style():
    """Apply treeview styling."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Weights.Treeview",
                    rowheight=30, font=(FONT_FAMILY, 10),
                    background=BG_SECONDARY, fieldbackground=BG_SECONDARY,
                    foreground=TEXT_PRIMARY, borderwidth=1, relief="solid")
    style.configure("Weights.Treeview.Heading",
                    font=(FONT_FAMILY, 10, "bold"),
                    background=BG_ELEVATED, foreground=ACCENT_GOLD,
                    relief="flat", padding=6, borderwidth=1)
    style.map("Weights.Treeview",
              background=[("selected", ACCENT_BLUE)],
              foreground=[("selected", "white")],
              fieldbackground=[("selected", ACCENT_BLUE)])


class WeightManagementScreen(ctk.CTkFrame):
    """Screen for managing item weights and pounds tracking."""

    def __init__(self, parent, db, user: dict, on_update=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self.user = user
        self.on_update = on_update
        self._current_month = db.get_current_month_year()
        _apply_treeview_style()
        self._build()
        self.load_weights()

    def _build(self):
        """Build the weight management screen."""
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text="Weight Management",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        # Month selector
        month_frame = ctk.CTkFrame(self, fg_color="transparent")
        month_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            month_frame, text="Month:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 8))

        self.month_var = tk.StringVar(value=self._current_month)
        self.month_menu = ctk.CTkOptionMenu(
            month_frame, variable=self.month_var,
            values=[self._current_month],
            command=self._on_month_changed
        )
        self.month_menu.pack(side="left", padx=(0, 20))

        # Summary stats
        self.summary_label = ctk.CTkLabel(
            month_frame, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.summary_label.pack(side="left")

        # Treeview card
        tf = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        tf.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 8))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        cols = ("item_name", "current_lbs", "donated_lbs", "discarded_lbs", "remaining_lbs")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", style="Weights.Treeview")
        
        for col, heading, width in [
            ("item_name", "Item Name", 250),
            ("current_lbs", "Current (lbs)", 120),
            ("donated_lbs", "Donated (lbs)", 120),
            ("discarded_lbs", "Discarded (lbs)", 130),
            ("remaining_lbs", "Remaining (lbs)", 130),
        ]:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=60, anchor="center")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Bind double-click to edit
        self.tree.bind("<Double-1>", self._on_item_double_click)

        # Action buttons
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 8))

        ctk.CTkButton(
            actions, text="✎ Edit", width=90, height=36,
            fg_color=ACCENT_BLUE, hover_color="#1d4ed8",
            text_color="white", corner_radius=8,
            command=self._edit_selected,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            actions, text="↻ Refresh", width=90, height=36,
            fg_color=BG_SECONDARY, hover_color=BG_CARD,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self.load_weights,
        ).pack(side="left", padx=4)

        self.count_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.count_lbl.grid(row=4, column=0, sticky="w", padx=24, pady=(0, 10))

    def _on_month_changed(self, month):
        """Handle month selection change."""
        self._current_month = month
        self.load_weights()

    def load_weights(self):
        """Load and display weights for the selected month."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load weights from database
        try:
            # For current month, get from inventory_items
            if self._current_month == self.db.get_current_month_year():
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    SELECT id, item_name, current_pounds, donated_pounds,
                           discarded_pounds, calculated_remaining
                    FROM inventory_items
                    WHERE current_pounds > 0 OR donated_pounds > 0 OR discarded_pounds > 0
                    ORDER BY item_name
                """)
                rows = cursor.fetchall()
            else:
                # For past months, get from weight_history
                cursor = self.db.conn.cursor()
                cursor.execute("""
                    SELECT i.id, i.item_name, wh.current_pounds, wh.donated_pounds,
                           wh.discarded_pounds, wh.calculated_remaining
                    FROM weight_history wh
                    JOIN inventory_items i ON wh.item_id = i.id
                    WHERE wh.month_year = ?
                    ORDER BY i.item_name
                """, (self._current_month,))
                rows = cursor.fetchall()

            # Add rows to treeview
            for row in rows:
                item_id, name, current, donated, discarded, remaining = row
                self.tree.insert("", "end", iid=str(item_id), values=(
                    name,
                    f"{current:.2f}",
                    f"{donated:.2f}",
                    f"{discarded:.2f}",
                    f"{remaining:.2f}",
                ))

            # Update summary
            summary = self.db.get_weight_summary(self._current_month)
            self.summary_label.configure(
                text=f"Total: {summary['total_current']:.2f} lbs current | "
                     f"{summary['total_donated']:.2f} lbs donated | "
                     f"{summary['total_discarded']:.2f} lbs discarded | "
                     f"{summary['total_remaining']:.2f} lbs remaining"
            )

            self.count_lbl.configure(
                text=f"{summary['item_count']} item(s) with weight data"
            )

            # Update month menu with available months
            months = self.db.get_all_months()
            if months:
                self.month_menu.configure(values=months)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load weights: {str(e)}")

    def _on_item_double_click(self, event):
        """Handle double-click on item to edit."""
        self._edit_selected()

    def _edit_selected(self):
        """Edit the selected item's weights."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select an item first.")
            return

        item_id = int(sel[0])
        try:
            item = self.db.get_item_by_id(item_id)
            if item:
                WeightEntryDialog(self, self.db, item, self.user, on_complete=self.load_weights)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load item: {str(e)}")
