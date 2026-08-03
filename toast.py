"""
toast.py — Non-blocking toast notification system.

Usage:
    from toast import Toast
    Toast.show(parent_widget, "Scan In Complete", kind="success")
    Toast.show(parent_widget, "Item Not Found",   kind="error")
    Toast.show(parent_widget, "Low Stock",        kind="warning")
    Toast.show(parent_widget, "Info message",     kind="info")
"""

import tkinter as tk
from theme import (
    ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    ACCENT_GOLD, BG_CARD, TEXT_PRIMARY, FONT_FAMILY
)

_KINDS = {
    "success": (ACCENT_GREEN,  "✓"),
    "error":   (ACCENT_RED,    "✕"),
    "warning": (ACCENT_AMBER,  "⚠"),
    "info":    (ACCENT_BLUE,   "ℹ"),
    "gold":    (ACCENT_GOLD,   "★"),
}

_DURATION = 3200   # ms before auto-dismiss
_SLIDE_MS  = 18    # ms per animation step
_SLIDE_PX  = 3     # px per animation step


class _ToastWidget(tk.Frame):
    def __init__(self, root: tk.Misc, message: str, kind: str):
        accent, icon = _KINDS.get(kind, _KINDS["info"])
        super().__init__(
            root,
            bg=BG_CARD,
            highlightbackground=accent,
            highlightthickness=2,
            bd=0,
            cursor="hand2",
        )

        # Left color stripe
        stripe = tk.Frame(self, bg=accent, width=5)
        stripe.pack(side="left", fill="y")

        # Icon
        tk.Label(
            self, text=icon, bg=BG_CARD,
            fg=accent, font=(FONT_FAMILY, 14, "bold"),
            padx=8,
        ).pack(side="left")

        # Message
        tk.Label(
            self, text=message, bg=BG_CARD,
            fg=TEXT_PRIMARY, font=(FONT_FAMILY, 11, "normal"),
            padx=4, pady=12, wraplength=280, justify="left",
        ).pack(side="left", fill="x", expand=True)

        # Close button
        close = tk.Label(
            self, text="×", bg=BG_CARD,
            fg="#64748B", font=(FONT_FAMILY, 14, "bold"),
            padx=10, cursor="hand2",
        )
        close.pack(side="right")
        close.bind("<Button-1>", lambda _: self._dismiss())
        self.bind("<Button-1>", lambda _: self._dismiss())

    def _dismiss(self):
        self.place_forget()
        try:
            self.destroy()
        except Exception:
            pass


class Toast:
    """Static helper — call Toast.show() from anywhere."""

    _stack: list = []   # active toasts per root window

    @classmethod
    def show(cls, parent: tk.Misc, message: str, kind: str = "info",
             duration: int = _DURATION):
        """Display a toast notification anchored to the top-right of *parent*."""
        root = parent.winfo_toplevel()

        toast = _ToastWidget(root, message, kind)
        toast.place(relx=1.0, rely=0.0, anchor="ne", x=-16, y=-60)

        cls._stack.append(toast)
        cls._slide_in(root, toast, duration)

    # ----------------------------------------------------------------

    @classmethod
    def _slide_in(cls, root: tk.Misc, toast: _ToastWidget, duration: int):
        target_y = 16
        current = [0]

        def _step():
            if not toast.winfo_exists():
                return
            current[0] = min(current[0] + _SLIDE_PX, target_y)
            toast.place_configure(y=current[0])
            if current[0] < target_y:
                root.after(_SLIDE_MS, _step)
            else:
                root.after(duration, lambda: cls._fade_out(root, toast))

        _step()

    @classmethod
    def _fade_out(cls, root: tk.Misc, toast: _ToastWidget):
        current = [16]

        def _step():
            if not toast.winfo_exists():
                return
            current[0] -= _SLIDE_PX
            toast.place_configure(y=current[0])
            if current[0] > -60:
                root.after(_SLIDE_MS, _step)
            else:
                try:
                    cls._stack.remove(toast)
                except ValueError:
                    pass
                toast.destroy()

        _step()
