"""
item_suggestion_dialog.py — Dialog showing multiple AI suggestions for user selection.

Displays multiple item suggestions with confidence scores and allows user to select
the most accurate option.
"""

import customtkinter as ctk
from typing import Callable, Optional, List, Dict
from font_config import FONT_LABEL_MEDIUM, FONT_BODY_MEDIUM, FONT_BUTTON_MEDIUM, FONT_BODY_SMALL
from theme import (
    BG_BASE, BG_ELEVATED, BG_HOVER,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER_COLOR, BORDER_SUBTLE
)


class ItemSuggestionDialog(ctk.CTkToplevel):
    """Dialog showing multiple item suggestions from AI."""

    def __init__(
        self,
        parent,
        suggestions: List[Dict],
        on_select: Callable,
        on_cancel: Callable = None
    ):
        """Initialize suggestion dialog.
        
        Args:
            parent: Parent window
            suggestions: List of suggestion dictionaries
            on_select: Callback when user selects a suggestion
            on_cancel: Callback when user cancels
        """
        super().__init__(parent)
        self.title("AI Item Suggestions")
        self.geometry("750x700")
        self.resizable(False, False)
        
        self.suggestions = suggestions
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.selected = None
        
        self._build()
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _build(self):
        """Build dialog UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 12))
        
        ctk.CTkLabel(
            header,
            text="🤖 AI Item Suggestions",
            font=FONT_LABEL_MEDIUM,
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header,
            text=f"Select the most accurate option ({len(self.suggestions)} suggestions available)",
            font=FONT_BODY_SMALL,
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(4, 0))

        # Suggestions frame
        self.suggestions_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_BASE
        )
        self.suggestions_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Display each suggestion
        for i, suggestion in enumerate(self.suggestions):
            self._add_suggestion_card(i, suggestion)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            font=FONT_BUTTON_MEDIUM,
            fg_color=BG_ELEVATED,
            hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
            command=self._on_cancel,
            width=100
        ).pack(side="right", padx=(8, 0))

    def _add_suggestion_card(self, index: int, suggestion: Dict):
        """Add a suggestion card to the dialog.
        
        Args:
            index: Suggestion index
            suggestion: Suggestion data
        """
        card = ctk.CTkFrame(
            self.suggestions_frame,
            fg_color=BG_ELEVATED,
            corner_radius=12,
            border_width=2,
            border_color=BORDER_SUBTLE
        )
        card.pack(fill="x", pady=8, padx=0)
        card.configure(cursor="hand2")

        # Make card clickable
        card.bind("<Button-1>", lambda e: self._on_select(index))

        # Header with number and confidence
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 8))

        # Number and item name
        name_frame = ctk.CTkFrame(header, fg_color="transparent")
        name_frame.pack(anchor="w", side="left", fill="x", expand=True)

        ctk.CTkLabel(
            name_frame,
            text=f"Option {index + 1}: {suggestion.get('item_name', 'Unknown')}",
            font=FONT_LABEL_MEDIUM,
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        # Confidence badge
        confidence = suggestion.get("confidence", 0)
        if confidence > 0.85:
            conf_color = ACCENT_GREEN
            conf_text = f"✓ {confidence*100:.0f}% Confident"
        elif confidence > 0.70:
            conf_color = ACCENT_AMBER
            conf_text = f"~ {confidence*100:.0f}% Confident"
        else:
            conf_color = ACCENT
            conf_text = f"○ {confidence*100:.0f}% Confident"

        ctk.CTkLabel(
            header,
            text=conf_text,
            font=FONT_BODY_SMALL,
            text_color=conf_color
        ).pack(anchor="e", side="right")

        # Details
        details_frame = ctk.CTkFrame(card, fg_color="transparent")
        details_frame.pack(fill="x", padx=12, pady=(0, 12))

        # Category and shelf life
        info_text = f"Category: {suggestion.get('category', 'N/A')} | Shelf Life: {suggestion.get('shelf_life_days', 365)} days"
        ctk.CTkLabel(
            details_frame,
            text=info_text,
            font=FONT_BODY_SMALL,
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 4))

        # Source
        source_text = f"Source: {suggestion.get('source', 'Unknown')}"
        ctk.CTkLabel(
            details_frame,
            text=source_text,
            font=FONT_BODY_SMALL,
            text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(0, 4))

        # Notes
        notes = suggestion.get('notes', '')
        if notes:
            ctk.CTkLabel(
                details_frame,
                text=notes,
                font=FONT_BODY_SMALL,
                text_color=TEXT_SECONDARY,
                wraplength=650
            ).pack(anchor="w", pady=(0, 4))

        # Make entire card clickable
        for widget in card.winfo_children():
            widget.bind("<Button-1>", lambda e: self._on_select(index))
            widget.configure(cursor="hand2")
            for child in widget.winfo_children():
                child.bind("<Button-1>", lambda e: self._on_select(index))
                child.configure(cursor="hand2")

    def _on_select(self, index: int):
        """Handle suggestion selection.
        
        Args:
            index: Selected suggestion index
        """
        self.selected = self.suggestions[index]
        if self.on_select:
            self.on_select(self.selected)
        self.destroy()

    def _on_cancel(self):
        """Handle cancel."""
        if self.on_cancel:
            self.on_cancel()
        self.destroy()
