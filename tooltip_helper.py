"""tooltip_helper.py — Tooltip utility for CustomTkinter widgets.

Provides a simple, non-intrusive tooltip system for UI elements.
Tooltips appear on hover and disappear when the mouse leaves.
"""

import tkinter as tk
from typing import Optional
import customtkinter as ctk


class Tooltip:
    """Simple tooltip that appears on hover."""

    def __init__(self, widget, text: str, delay_ms: int = 500):
        """
        Create a tooltip for a widget.
        
        Args:
            widget: The CTkinter widget to attach the tooltip to
            text: The tooltip text to display
            delay_ms: Delay in milliseconds before showing tooltip (default 500ms)
        """
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tipwindow: Optional[tk.Toplevel] = None
        self.id: Optional[str] = None
        self.x = self.y = 0

        # Bind hover events
        self._bind_events()

    def _bind_events(self):
        """Bind hover events to the widget."""
        try:
            # Try direct binding first
            self.widget.bind("<Enter>", self._on_enter, add=True)
            self.widget.bind("<Leave>", self._on_leave, add=True)
            self.widget.bind("<Motion>", self._on_motion, add=True)
        except Exception:
            # If that fails, try binding to all child widgets
            try:
                for child in self.widget.winfo_children():
                    child.bind("<Enter>", self._on_enter, add=True)
                    child.bind("<Leave>", self._on_leave, add=True)
                    child.bind("<Motion>", self._on_motion, add=True)
            except Exception:
                pass

    def _on_enter(self, event):
        """Show tooltip after delay."""
        if self.tipwindow or not self.text:
            return
        self.id = self.widget.after(self.delay_ms, self._show_tooltip, event)

    def _on_leave(self, event):
        """Hide tooltip when mouse leaves."""
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        self._hide_tooltip()

    def _on_motion(self, event):
        """Update tooltip position on mouse motion."""
        if self.tipwindow:
            self.x = event.x_root + 10
            self.y = event.y_root + 10
            self.tipwindow.geometry(f"+{self.x}+{self.y}")

    def _show_tooltip(self, event):
        """Display the tooltip."""
        if self.tipwindow or not self.text:
            return

        self.x = event.x_root + 10
        self.y = event.y_root + 10

        # Create tooltip window
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{self.x}+{self.y}")

        # Create label with tooltip text
        label = tk.Label(
            tw,
            text=self.text,
            background="#2b2b2b",
            foreground="#e0e0e0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Helvetica", 9),
            padx=8,
            pady=4,
            wraplength=250,
            justify=tk.LEFT,
        )
        label.pack(ipadx=1)

        # Ensure tooltip stays on top
        tw.attributes("-topmost", True)

    def _hide_tooltip(self):
        """Hide the tooltip."""
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


def add_tooltip(widget, text: str, delay_ms: int = 500) -> Tooltip:
    """
    Convenience function to add a tooltip to a widget.
    
    Args:
        widget: The CTkinter widget
        text: The tooltip text
        delay_ms: Delay before showing (default 500ms)
    
    Returns:
        The Tooltip object (can be ignored if not needed)
    """
    return Tooltip(widget, text, delay_ms)
