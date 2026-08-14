"""
intake_screen_pos.py — POS-style intake screen with shopping cart.

Features:
- Client selection at top
- Barcode scanner input
- Real-time cart display
- Quantity adjustment
- Item removal
- Transaction complete/cancel
- Receipt generation
"""

import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable
from datetime import datetime

from intake_cart import IntakeCart
from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
)
from font_config import FONT_LABEL_MEDIUM, FONT_BODY_MEDIUM, FONT_BUTTON_MEDIUM
from toast import Toast


class IntakeScreenPOS(ctk.CTkFrame):
    """POS-style intake screen with shopping cart."""

    def __init__(self, parent, db, user):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db = db
        self.user = user
        self.cart = IntakeCart(db)
        self._lookup_timer = None
        
        self._build()

    def _build(self):
        """Build the POS layout."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(2, weight=1)

        # Top: Transaction type selector
        self._build_transaction_type(main)

        # Left side: Scanner and client
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=1, column=0, sticky="ew", padx=(0, 20))
        left.grid_columnconfigure(0, weight=1)

        self._build_client_selector(left)
        self._build_barcode_input(left)

        # Right side: Cart
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=(20, 0))
        right.grid_rowconfigure(1, weight=1)

        self._build_cart_header(right)
        self._build_cart_display(right)
        self._build_cart_footer(right)

        # Bottom: Actions
        bottom = ctk.CTkFrame(main, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        bottom.grid_columnconfigure(0, weight=1)

        self._build_actions(bottom)

    def _build_transaction_type(self, parent):
        """Build transaction type selector (IN or OUT)."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        frame.grid_columnconfigure(0, weight=1)

        # Label
        ctk.CTkLabel(
            frame, text="TRANSACTION TYPE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(0, 8))

        # Button frame
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        self.transaction_type = tk.StringVar(value="OUT")

        # Scan OUT button (Distribution to client)
        self.btn_scan_out = ctk.CTkButton(
            btn_frame, text="📤 SCAN OUT (Distribution)", height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=ACCENT_RED, hover_color="#cc0000",
            text_color="white",
            command=lambda: self._set_transaction_type("OUT")
        )
        self.btn_scan_out.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Scan IN button (Receiving items)
        self.btn_scan_in = ctk.CTkButton(
            btn_frame, text="📥 SCAN IN (Receiving)", height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=ACCENT_GREEN, hover_color="#00aa00",
            text_color="white",
            command=lambda: self._set_transaction_type("IN")
        )
        self.btn_scan_in.grid(row=0, column=1, sticky="ew")

        # Status label
        self.transaction_status_label = ctk.CTkLabel(
            frame, text="📤 Distribution Mode: Scanning items to give to client",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=ACCENT_RED
        )
        self.transaction_status_label.pack(anchor="w", pady=(8, 0))

    def _set_transaction_type(self, trans_type):
        """Set transaction type (IN or OUT)."""
        self.transaction_type.set(trans_type)
        
        if trans_type == "OUT":
            self.btn_scan_out.configure(fg_color=ACCENT_RED, hover_color="#cc0000")
            self.btn_scan_in.configure(fg_color=BG_ELEVATED, hover_color=BG_HOVER)
            self.transaction_status_label.configure(
                text="📤 Distribution Mode: Select client to scan items for",
                text_color=ACCENT_RED
            )
            # SHOW client selector for SCAN OUT
            self.client_frame.pack(fill="x", pady=(0, 16))
            # Focus on client search field
            self.after(100, lambda: self.client_entry.focus())
        else:  # IN
            self.btn_scan_in.configure(fg_color=ACCENT_GREEN, hover_color="#00aa00")
            self.btn_scan_out.configure(fg_color=BG_ELEVATED, hover_color=BG_HOVER)
            self.transaction_status_label.configure(
                text="📥 Receiving Mode: Scanning items coming into pantry (no client needed)",
                text_color=ACCENT_GREEN
            )
            # HIDE client selector for SCAN IN
            self.client_frame.pack_forget()
        
        # Clear cart and client when switching modes
        self.client_search_var.set("")
        self.cart.cancel_transaction()
        self._update_cart_display()

    def _build_client_selector(self, parent):
        """Build client selection with searchable dropdown (SCAN OUT only)."""
        # Only show for SCAN OUT (distribution)
        self.client_frame = ctk.CTkFrame(parent, fg_color=BG_ELEVATED, corner_radius=12,
                            border_width=1, border_color=BORDER_SUBTLE)
        self.client_frame.pack(fill="x", pady=(0, 16))
        self.client_frame.grid_columnconfigure(0, weight=1)
        
        # Store reference for show/hide
        self._client_frame_widget = self.client_frame

        # Header with label and help text
        header = ctk.CTkFrame(self.client_frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="CLIENT",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    text_color=TEXT_MUTED).pack(anchor="w", side="left")

        ctk.CTkLabel(header, text="Search by name or student ID",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                    text_color=TEXT_MUTED).pack(anchor="e", side="right")

        # Search/input frame
        input_frame = ctk.CTkFrame(self.client_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=16, pady=(0, 8))
        input_frame.grid_columnconfigure(0, weight=1)

        self.client_search_var = tk.StringVar()
        self.client_search_var.trace_add("write", self._on_client_search)

        self.client_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.client_search_var,
            placeholder_text="Type name or student ID...",
            height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            fg_color=BG_OVERLAY,
            border_color=ACCENT,
            border_width=2,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
        )
        self.client_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.client_entry.bind("<Escape>", lambda e: self.client_search_var.set(""))

        # Clear button
        ctk.CTkButton(
            input_frame, text="✕", width=40, height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=ACCENT_RED, hover_color="#cc0000",
            command=lambda: self.client_search_var.set("")
        ).grid(row=0, column=1, padx=(0, 8))

        # Refresh button
        ctk.CTkButton(
            input_frame, text="↻", width=40, height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=ACCENT, hover_color="#FF9500",
            command=self._refresh_client_list
        ).grid(row=0, column=2)

        # Dropdown frame (scrollable list)
        self.client_dropdown_frame = ctk.CTkScrollableFrame(
            self.client_frame, fg_color=BG_OVERLAY, corner_radius=8,
            border_width=1, border_color=BORDER_SUBTLE,
            height=150
        )
        self.client_dropdown_frame.pack(fill="both", expand=False, padx=16, pady=(0, 12))
        self.client_dropdown_frame.grid_columnconfigure(0, weight=1)

        self.clients_data = []
        self.client_buttons = []

        # Load clients on startup
        self._refresh_client_list()

    def _refresh_client_list(self):
        """Refresh the client dropdown list."""
        try:
            clients = self.db.get_all_pantry_clients() or []
            self.clients_data = clients
            self.client_search_var.set("")
            self._update_client_dropdown()
        except Exception as e:
            print(f"Error refreshing clients: {e}")

    def _on_client_search(self, *args):
        """Handle client search input."""
        self._update_client_dropdown()

    def _update_client_dropdown(self):
        """Update the dropdown list based on search."""
        # Clear existing buttons
        for btn in self.client_buttons:
            btn.destroy()
        self.client_buttons = []

        search_text = self.client_search_var.get().lower().strip()
        print(f"DEBUG: _update_client_dropdown called with search_text='{search_text}'")

        # If no search text, show all clients
        if not search_text:
            filtered = self.clients_data
            print(f"DEBUG: No search text, showing all {len(self.clients_data)} clients")
        else:
            # Filter clients based on search
            filtered = []
            for client in self.clients_data:
                first = client.get('first_name', '').lower()
                last = client.get('last_name', '').lower()
                full_name = f"{first} {last}".strip()
                student_id = client.get('student_id', '').lower()
                
                # Check if search text matches any field
                if (search_text in first or 
                    search_text in last or 
                    search_text in full_name or 
                    search_text in student_id):
                    filtered.append(client)
            print(f"DEBUG: Found {len(filtered)} matching clients")

        # Show message if no results
        if not filtered:
            print(f"DEBUG: No clients found, showing message")
            msg_label = ctk.CTkLabel(
                self.client_dropdown_frame,
                text="No clients found",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED
            )
            msg_label.pack(pady=8)
            self.client_buttons.append(msg_label)
            return

        # Create buttons for each client
        print(f"DEBUG: Creating {len(filtered[:20])} client buttons")
        for client in filtered[:20]:  # Limit to 20 results
            first_name = client.get('first_name', '').strip()
            last_name = client.get('last_name', '').strip()
            student_id = client.get('student_id', '').strip()
            client_id = client.get('id')
            
            # Build display text
            btn_text = f"{first_name} {last_name}".strip()
            if student_id:
                btn_text += f" ({student_id})"

            print(f"DEBUG: Creating button for client: {btn_text} (ID: {client_id})")
            
            btn = ctk.CTkButton(
                self.client_dropdown_frame,
                text=btn_text,
                height=36,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                fg_color=BG_ELEVATED,
                hover_color=BG_HOVER,
                text_color=TEXT_PRIMARY,
                anchor="w",
                command=lambda c=client: self._select_client(c)
            )
            btn.pack(fill="x", padx=8, pady=4)
            self.client_buttons.append(btn)
            print(f"DEBUG: Button created and packed")

    def _select_client(self, client):
        """Select a client from the dropdown."""
        client_id = client.get('id')
        client_name = f"{client.get('first_name', '')} {client.get('last_name', '')}"

        print(f"DEBUG: Selecting client: {client_name} (ID: {client_id})")
        
        # Cancel any existing transaction first
        if self.cart.is_transaction_active():
            print(f"DEBUG: Cancelling existing transaction before starting new one")
            self.cart.cancel_transaction()
        
        success, msg = self.cart.start_transaction(client_id, client_name)
        print(f"DEBUG: start_transaction result: success={success}, msg={msg}")
        
        if success:
            print(f"DEBUG: Transaction started successfully")
            Toast.show(self, msg, "success")
            self.client_search_var.set(client_name)
            self._update_cart_display()
            self.barcode_entry.focus()
        else:
            print(f"DEBUG: Transaction failed: {msg}")
            Toast.show(self, msg, "error")

    def _build_barcode_input(self, parent):
        """Build barcode input field."""
        frame = ctk.CTkFrame(parent, fg_color=BG_ELEVATED, corner_radius=12,
                            border_width=1, border_color=BORDER_SUBTLE)
        frame.pack(fill="x", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="BARCODE",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                    text_color=TEXT_MUTED).pack(anchor="w", padx=16, pady=(12, 4))

        self.barcode_var = tk.StringVar()
        self.barcode_var.trace_add("write", self._on_barcode_change)

        self.barcode_entry = ctk.CTkEntry(
            frame,
            textvariable=self.barcode_var,
            placeholder_text="Scan or type barcode...",
            height=44,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            fg_color=BG_OVERLAY,
            border_color=ACCENT,
            border_width=2,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
        )
        self.barcode_entry.pack(fill="x", padx=16, pady=(0, 12))
        self.barcode_entry.bind("<Return>", lambda _: self._on_barcode_scanned())

    def _on_barcode_change(self, *args):
        """Handle barcode input change."""
        # Clear any pending timer
        if self._lookup_timer:
            self.after_cancel(self._lookup_timer)

        # Set new timer for lookup
        self._lookup_timer = self.after(350, self._lookup_barcode)

    def _lookup_barcode(self):
        """Look up barcode in database."""
        barcode = self.barcode_var.get().strip()
        if not barcode:
            return

        try:
            item = self.db.get_item_by_barcode(barcode)
            if item:
                self._show_item_preview(item)
        except Exception as e:
            print(f"Lookup error: {e}")

    def _show_item_preview(self, item):
        """Show item preview before adding."""
        # This could show a preview dialog or just add directly
        # For now, we'll add directly on Enter
        pass

    def _on_barcode_scanned(self):
        """Handle barcode scan (Enter pressed)."""
        trans_type = self.transaction_type.get()
        print(f"DEBUG: Barcode scan - trans_type={trans_type}")
        
        # For SCAN OUT, require client selection
        if trans_type == "OUT":
            is_active = self.cart.is_transaction_active()
            print(f"DEBUG: SCAN OUT mode - transaction active: {is_active}")
            if not is_active:
                print(f"DEBUG: No transaction active, showing warning")
                Toast.show(self, "Please select a client first", "warning")
                self.barcode_entry.delete(0, "end")
                return
        else:  # SCAN IN
            # For SCAN IN, start transaction if not already active
            if not self.cart.is_transaction_active():
                print(f"DEBUG: SCAN IN mode - starting transaction")
                self.cart.start_transaction(0, "Receiving Items")

        barcode = self.barcode_var.get().strip().upper()  # Normalize to uppercase
        print(f"DEBUG: Looking up barcode: {barcode}")
        if not barcode:
            return

        try:
            item = self.db.get_item_by_barcode(barcode)
            print(f"DEBUG: Barcode lookup result: {item}")
            if not item:
                Toast.show(self, f"Item not found: {barcode}", "error")
                self.barcode_entry.delete(0, "end")
                return

            # Get category, with AI auto-fill if missing
            category = item.get("category", "").strip()
            if not category:
                category = self._get_ai_category(item.get("item_name", ""))

            # Add to cart
            success, msg = self.cart.add_item(
                item_id=item.get("id"),
                barcode=item.get("barcode"),
                item_name=item.get("item_name"),
                quantity=1,
                category=category,
                storage_location=item.get("storage_location", "")
            )

            if success:
                Toast.show(self, msg, "success")
                self._update_cart_display()
                self.barcode_entry.delete(0, "end")
                self.barcode_entry.focus()
            else:
                Toast.show(self, msg, "error")
        except Exception as e:
            print(f"Barcode scan error: {e}")
            Toast.show(self, f"Error: {str(e)}", "error")
            self.barcode_entry.delete(0, "end")

    def _get_ai_category(self, item_name: str) -> str:
        """Use AI to guess category from item name based on PACKAGING TYPE.
        
        Categories are based on HOW the item is packaged/formatted:
        - Canned Item: In a can
        - Boxed Item: In a box
        - Bagged Item: In a bag
        - Jarred Item: In a jar
        - Bottled Item: In a bottle
        - Dry Item: Dry goods (beans, rice, etc.)
        - Fresh Item: Fresh produce
        """
        if not item_name:
            return "Uncategorized"
        
        item_lower = item_name.lower()
        
        # Check for packaging type first (highest priority)
        packaging_keywords = {
            "Canned Item": ["can", "canned", "tin", "soup", "stew", "chili", "ravioli"],
            "Boxed Item": ["box", "boxed", "mac & cheese", "helper", "meal", "ramen"],
            "Bagged Item": ["bag", "bagged", "cereal", "chips", "crackers", "snack", "flakes"],
            "Jarred Item": ["jar", "jarred", "peanut butter", "jelly", "sauce"],
            "Bottled Item": ["bottle", "bottled", "drink", "juice", "milk"],
            "Dry Item": ["dry", "dried", "bean", "lentil", "rice", "grain", "oatmeal", "grits", "pasta", "noodle"],
            "Fresh Item": ["fresh", "produce", "vegetable", "fruit"],
        }
        
        # Check packaging type
        for category, keywords in packaging_keywords.items():
            for keyword in keywords:
                if keyword in item_lower:
                    return category
        
        # Default category
        return "Uncategorized"

    def _build_cart_header(self, parent):
        """Build cart header."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="CART",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                    text_color=TEXT_PRIMARY).pack(anchor="w")

        self.cart_info_label = ctk.CTkLabel(
            header, text="0 items • 0 units",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY
        )
        self.cart_info_label.pack(anchor="w", pady=(2, 0))

    def _build_cart_display(self, parent):
        """Build cart items display."""
        self.cart_frame = ctk.CTkScrollableFrame(
            parent, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_SUBTLE
        )
        self.cart_frame.pack(fill="both", expand=True, pady=(0, 12))
        self.cart_frame.grid_columnconfigure(0, weight=1)

        self.cart_items_frame = ctk.CTkFrame(self.cart_frame, fg_color="transparent")
        self.cart_items_frame.pack(fill="both", expand=True, padx=12, pady=12)
        self.cart_items_frame.grid_columnconfigure(0, weight=1)

        self._update_cart_display()

    def _update_cart_display(self):
        """Update cart display with current items."""
        # Clear existing items
        for widget in self.cart_items_frame.winfo_children():
            widget.destroy()

        summary = self.cart.get_cart_summary()

        if "error" in summary:
            ctk.CTkLabel(
                self.cart_items_frame,
                text="No transaction active",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED
            ).pack(pady=20)
            self.cart_info_label.configure(text="0 items • 0 units")
            return

        items = summary.get("items", [])
        if not items:
            ctk.CTkLabel(
                self.cart_items_frame,
                text="Cart is empty",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED
            ).pack(pady=20)
            self.cart_info_label.configure(text="0 items • 0 units")
            return

        # Display each item
        for item in items:
            self._add_cart_item_display(item)

        # Update info
        item_count = len(items)
        total_units = summary.get("total_units", 0)
        self.cart_info_label.configure(text=f"{item_count} items • {total_units} units")

    def _add_cart_item_display(self, item):
        """Add a single cart item display."""
        item_frame = ctk.CTkFrame(
            self.cart_items_frame, fg_color=BG_OVERLAY, corner_radius=8,
            border_width=1, border_color=BORDER_SUBTLE
        )
        item_frame.pack(fill="x", pady=6)
        item_frame.grid_columnconfigure(0, weight=1)

        # Item name and barcode
        name_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        name_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            name_frame, text=item["item_name"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", side="left")

        ctk.CTkLabel(
            name_frame, text=item["barcode"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED
        ).pack(anchor="e", side="right")

        # Quantity controls
        qty_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        qty_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 8))
        qty_frame.grid_columnconfigure(1, weight=1)

        # Minus button
        ctk.CTkButton(
            qty_frame, text="−", width=30, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=ACCENT_RED, hover_color="#cc0000",
            command=lambda: self._adjust_quantity(item["barcode"], -1)
        ).grid(row=0, column=0, padx=(0, 6))

        # Quantity display
        qty_label = ctk.CTkLabel(
            qty_frame, text=f"{item['quantity']} units",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        qty_label.grid(row=0, column=1)

        # Plus button
        ctk.CTkButton(
            qty_frame, text="+", width=30, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=ACCENT_GREEN, hover_color="#00aa00",
            command=lambda: self._adjust_quantity(item["barcode"], 1)
        ).grid(row=0, column=2, padx=(6, 0))

        # Remove button
        ctk.CTkButton(
            qty_frame, text="Remove", width=60, height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            fg_color=ACCENT_RED, hover_color="#cc0000",
            command=lambda: self._remove_item(item["barcode"])
        ).grid(row=0, column=3, padx=(12, 0))

    def _adjust_quantity(self, barcode, delta):
        """Adjust item quantity."""
        item = self.cart.get_item_in_cart(barcode)
        if item:
            new_qty = item.quantity + delta
            success, msg = self.cart.update_quantity(barcode, new_qty)
            if success:
                self._update_cart_display()
            else:
                Toast.show(self, msg, "error")

    def _remove_item(self, barcode):
        """Remove item from cart."""
        success, msg = self.cart.remove_item(barcode)
        if success:
            Toast.show(self, msg, "success")
            self._update_cart_display()
        else:
            Toast.show(self, msg, "error")

    def _build_cart_footer(self, parent):
        """Build cart footer with total."""
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.pack(fill="x", pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)

        # Total frame
        total_frame = ctk.CTkFrame(footer, fg_color=BG_ELEVATED, corner_radius=8,
                                  border_width=1, border_color=BORDER_SUBTLE)
        total_frame.pack(fill="x", pady=(0, 12))
        total_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            total_frame, text="TOTAL",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.total_label = ctk.CTkLabel(
            total_frame, text="0 items",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.total_label.pack(anchor="w", padx=12, pady=(0, 8))

    def _build_actions(self, parent):
        """Build action buttons."""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        # Complete button
        ctk.CTkButton(
            button_frame, text="✓ Complete Transaction", height=50,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=ACCENT_GREEN, hover_color="#00aa00",
            text_color="white",
            command=self._complete_transaction
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Cancel button
        ctk.CTkButton(
            button_frame, text="✕ Cancel", height=50,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=ACCENT_RED, hover_color="#cc0000",
            text_color="white",
            command=self._cancel_transaction
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _complete_transaction(self):
        """Complete the transaction."""
        if not self.cart.is_transaction_active():
            Toast.show(self, "No transaction in progress", "warning")
            return

        summary = self.cart.get_cart_summary()
        if "error" in summary or not summary.get("items"):
            Toast.show(self, "Cart is empty. Add items before completing.", "warning")
            return

        success, msg, data = self.cart.complete_transaction()
        if success:
            Toast.show(self, f"✓ Completed: {data['total_units']} units to {data['client_name']}", "success")
            self._reset_form()
        else:
            Toast.show(self, msg, "error")

    def _cancel_transaction(self):
        """Cancel the transaction."""
        if not self.cart.is_transaction_active():
            Toast.show(self, "No transaction in progress", "warning")
            return

        success, msg = self.cart.cancel_transaction()
        if success:
            Toast.show(self, msg, "success")
            self._reset_form()
        else:
            Toast.show(self, msg, "error")

    def _reset_form(self):
        """Reset form to initial state."""
        self.client_var.set("Select a client...")
        self.barcode_var.set("")
        self._update_cart_display()
        self.client_combo.focus()
