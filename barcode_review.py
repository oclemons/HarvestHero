"""barcode_review.py — In-app barcode image review interface.

Provides a grid of barcode reference images with full-size preview,
search/filter, and status indicators.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk
import threading

from barcode_manager import get_manager
from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY,
    ACCENT, ACCENT_HOVER, ACCENT_GREEN, ACCENT_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)
from toast import Toast


class BarcodeReviewFrame(ctk.CTkFrame):
    """Frame for reviewing barcode reference images."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=BG_BASE, **kwargs)
        self.manager = get_manager()
        self._photo_cache = {}
        self._current_barcode = None
        self._load_thread = None
        
        self._build_ui()
        self._load_barcodes()

    def _build_ui(self):
        """Build the UI layout."""
        # Header
        header = ctk.CTkFrame(self, fg_color=BG_SURFACE, height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, text="Barcode Reference Images",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=16, pady=12)
        
        # Search box
        search_frame = ctk.CTkFrame(header, fg_color="transparent")
        search_frame.pack(side="right", padx=16, pady=12)
        
        ctk.CTkLabel(
            search_frame, text="Search:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 8))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var,
            placeholder_text="Filter by section...",
            width=200, height=32,
        )
        search_entry.pack(side="left")
        
        # Main content: grid + preview
        content = ctk.CTkFrame(self, fg_color=BG_BASE)
        content.pack(fill="both", expand=True, padx=12, pady=12)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=0)
        content.grid_rowconfigure(0, weight=1)
        
        # Left: scrollable grid of thumbnails
        grid_frame = ctk.CTkFrame(content, fg_color=BG_SURFACE, corner_radius=8)
        grid_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        grid_frame.grid_rowconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            grid_frame, text="Sections",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))
        
        # Scrollable canvas for thumbnails
        canvas = tk.Canvas(
            grid_frame, bg=BG_SURFACE, highlightthickness=0,
            relief="flat", width=200,
        )
        canvas.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        
        scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self.thumbnail_frame = ctk.CTkFrame(canvas, fg_color=BG_SURFACE)
        self.thumbnail_frame.grid_columnconfigure(0, weight=1)
        canvas.create_window(0, 0, window=self.thumbnail_frame, anchor="nw")
        
        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        self.thumbnail_frame.bind("<Configure>", on_frame_configure)
        
        # Right: preview
        preview_frame = ctk.CTkFrame(content, fg_color=BG_SURFACE, corner_radius=8)
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            preview_frame, text="Preview",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))
        
        self.preview_label = ctk.CTkLabel(
            preview_frame, text="Select a section to preview",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
            fg_color=BG_ELEVATED,
            corner_radius=8,
            width=400, height=500,
        )
        self.preview_label.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        
        # Status bar
        status_frame = ctk.CTkFrame(self, fg_color=BG_SURFACE, height=40)
        status_frame.pack(fill="x", padx=0, pady=0)
        status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            status_frame, text="Loading...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.status_label.pack(side="left", padx=16, pady=12)

    def _load_barcodes(self):
        """Load available barcodes in a background thread."""
        def load():
            barcodes = self.manager.get_available_barcodes()
            self.after(0, self._populate_grid, barcodes)
        
        self._load_thread = threading.Thread(target=load, daemon=True)
        self._load_thread.start()

    def _populate_grid(self, barcodes):
        """Populate the thumbnail grid."""
        # Clear existing
        for widget in self.thumbnail_frame.winfo_children():
            widget.destroy()
        
        if not barcodes:
            ctk.CTkLabel(
                self.thumbnail_frame, text="No barcode images found",
                text_color=TEXT_MUTED,
            ).pack(padx=12, pady=12)
            self.status_label.configure(text=f"No barcode images found")
            return
        
        # Create thumbnail buttons
        for barcode_name in barcodes:
            self._create_thumbnail_button(barcode_name)
        
        self.status_label.configure(text=f"Loaded {len(barcodes)} barcode sections")

    def _create_thumbnail_button(self, barcode_name: str):
        """Create a thumbnail button for a barcode."""
        btn_frame = ctk.CTkFrame(
            self.thumbnail_frame, fg_color=BG_ELEVATED, corner_radius=6,
            border_width=1, border_color=BORDER_COLOR,
        )
        btn_frame.pack(fill="x", padx=0, pady=4)
        btn_frame.grid_columnconfigure(0, weight=1)
        
        # Load thumbnail in background
        def load_thumb():
            thumb = self.manager.get_thumbnail(barcode_name, size=150)
            self.after(0, lambda: self._set_thumbnail, btn_frame, barcode_name, thumb)
        
        threading.Thread(target=load_thumb, daemon=True).start()
        
        # Placeholder
        label = ctk.CTkLabel(
            btn_frame, text=f"Section {barcode_name}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color="transparent",
        )
        label.pack(fill="x", padx=8, pady=8)
        
        # Store reference for later update
        btn_frame._label = label
        btn_frame._barcode_name = barcode_name
        
        # Click handler
        def on_click(e=None):
            self._select_barcode(barcode_name)
        
        btn_frame.bind("<Button-1>", on_click)
        label.bind("<Button-1>", on_click)

    def _set_thumbnail(self, btn_frame, barcode_name: str, thumb: Image.Image):
        """Update a thumbnail button with the loaded image."""
        if thumb:
            # Convert PIL image to PhotoImage
            photo = ImageTk.PhotoImage(thumb)
            self._photo_cache[barcode_name] = photo
            
            # Update label to show image
            label = btn_frame._label
            label.configure(image=photo, text="")
        else:
            error = self.manager.get_error(barcode_name)
            label = btn_frame._label
            label.configure(
                text=f"Section {barcode_name}\n(Failed to load)",
                text_color=ACCENT_RED,
            )

    def _select_barcode(self, barcode_name: str):
        """Select a barcode and show full preview."""
        self._current_barcode = barcode_name
        
        # Load full-size image
        def load_full():
            img = self.manager.load_image(barcode_name, max_width=400, max_height=500)
            self.after(0, lambda: self._show_preview, barcode_name, img)
        
        threading.Thread(target=load_full, daemon=True).start()

    def _show_preview(self, barcode_name: str, img: Image.Image):
        """Display the full-size preview."""
        if self._current_barcode != barcode_name:
            return  # User selected a different one
        
        if img:
            photo = ImageTk.PhotoImage(img)
            self._photo_cache[f"preview_{barcode_name}"] = photo
            self.preview_label.configure(image=photo, text="")
        else:
            error = self.manager.get_error(barcode_name)
            self.preview_label.configure(
                image="",
                text=f"Failed to load Section {barcode_name}\n\n{error}",
                text_color=ACCENT_RED,
            )

    def _on_search(self, *args):
        """Handle search filter changes."""
        query = self.search_var.get().lower()
        
        # Show/hide thumbnails based on search
        for widget in self.thumbnail_frame.winfo_children():
            if hasattr(widget, '_barcode_name'):
                barcode_name = widget._barcode_name
                if query in barcode_name.lower():
                    widget.pack(fill="x", padx=0, pady=4)
                else:
                    widget.pack_forget()

    def on_shown(self):
        """Called when the frame becomes visible."""
        # Refresh if needed
        pass
