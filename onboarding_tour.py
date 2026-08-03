"""onboarding_tour.py — Step-by-step guided tour overlay."""

import tkinter as tk

import customtkinter as ctk

from theme import (
    BG_CARD, BG_SECONDARY, BG_HOVER,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)

_STEPS = [
    {
        "title": "Welcome to Inventory Control Center",
        "body": (
            "This guided tour walks you through the core features of the app.\n\n"
            "You'll learn how to scan items, manage inventory, view reports, "
            "and use the AI assistant. Click  Next  to begin."
        ),
        "nav": None,
    },
    {
        "title": "Dashboard — Your Command Center",
        "body": (
            "The Dashboard shows real-time stats:\n\n"
            "  •  Total SKUs and units in stock\n"
            "  •  Low-stock and out-of-stock counts\n"
            "  •  Today's scan-in and scan-out activity\n"
            "  •  Recent transaction feed\n\n"
            "Click  Dashboard  in the left sidebar to get here any time."
        ),
        "nav": "dashboard",
    },
    {
        "title": "Scanning Items",
        "body": (
            "Use the  Scan  page to record item movement:\n\n"
            "  1. Click in the barcode field (it focuses automatically).\n"
            "  2. Scan or type the barcode — the app auto-detects direction.\n"
            "  3. Adjust the quantity if needed.\n"
            "  4. For Scan Out, enter the recipient's name.\n"
            "  5. Press  Enter  or click Scan In / Scan Out.\n\n"
            "Keyboard shortcuts:  F1  =  Scan In   ·   F2  =  Scan Out   ·   F3  =  Clear"
        ),
        "nav": "scan",
    },
    {
        "title": "Inventory List",
        "body": (
            "The  Inventory  page shows every item in the system.\n\n"
            "  •  Search by barcode, name, or category.\n"
            "  •  Status badges indicate OK / LOW STOCK / OUT OF STOCK.\n"
            "  •  Admins can add, edit, or delete items here.\n"
            "  •  Each item can have a Scan-In barcode and a Scan-Out barcode."
        ),
        "nav": "inventory",
    },
    {
        "title": "Transaction History",
        "body": (
            "The  History  page shows every scan event.\n\n"
            "  •  Filter by type (Scan In / Scan Out), date range, or recipient.\n"
            "  •  Export to CSV or Excel for reporting.\n"
            "  •  All scans are attributed to the logged-in user."
        ),
        "nav": "history",
    },
    {
        "title": "Reports",
        "body": (
            "The  Reports  page provides pre-built views:\n\n"
            "  •  Current Inventory snapshot\n"
            "  •  Low Stock and Out-of-Stock lists\n"
            "  •  Scan In / Scan Out history\n"
            "  •  Recipient giveaway history\n\n"
            "All reports can be exported to CSV or Excel."
        ),
        "nav": "reports",
    },
    {
        "title": "AI Assistant",
        "body": (
            "The  AI Insights  page provides intelligent analysis:\n\n"
            "  •  Inventory health score (0–100)\n"
            "  •  Automated alerts for stock issues\n"
            "  •  Fastest-moving items and stockout forecasts\n"
            "  •  Chat-style Q&A — ask anything about your inventory\n\n"
            "No API key needed — it works locally out of the box."
        ),
        "nav": "ai",
    },
    {
        "title": "User Management  (Admins only)",
        "body": (
            "The  Users  page lets admins:\n\n"
            "  •  Create new staff or admin accounts\n"
            "  •  Activate or deactivate users\n"
            "  •  Reset passwords\n"
            "  •  Change user roles\n\n"
            "Every scan is logged with the username of the person who performed it."
        ),
        "nav": "users",
    },
    {
        "title": "You're all set!",
        "body": (
            "That covers the essentials.  You can restart this tour any time "
            "from  Settings  →  Onboarding Tour.\n\n"
            "Tip: The sidebar collapses on smaller screens. "
            "Click the menu icon to expand it.\n\n"
            "Happy scanning!"
        ),
        "nav": None,
    },
]


class OnboardingTour(ctk.CTkToplevel):
    """Modal step-by-step tour window."""

    def __init__(self, parent, navigate_fn, on_complete):
        super().__init__(parent)
        self.navigate = navigate_fn
        self.on_complete = on_complete
        self._step = 0

        self.title("Getting Started")
        self.geometry("560x420")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color=BG_CARD)
        self.protocol("WM_DELETE_WINDOW", self._finish)

        self._build()
        self._show_step()
        self.after(100, self.lift)

    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Progress bar (dots)
        self._dot_row = ctk.CTkFrame(self, fg_color="transparent")
        self._dot_row.grid(row=0, column=0, pady=(20, 0))

        self._dots = []
        for i in range(len(_STEPS)):
            dot = ctk.CTkFrame(
                self._dot_row, width=10, height=10,
                fg_color=BORDER_COLOR, corner_radius=5)
            dot.pack(side="left", padx=3)
            self._dots.append(dot)

        # Content card
        content = ctk.CTkFrame(
            self, fg_color=BG_SECONDARY, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR)
        content.grid(row=1, column=0, sticky="nsew", padx=28, pady=16)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._title_lbl = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=ACCENT_GOLD, anchor="w", wraplength=460,
        )
        self._title_lbl.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        ctk.CTkFrame(content, height=1, fg_color=BORDER_COLOR).grid(
            row=1, column=0, sticky="ew", padx=20)

        self._body_lbl = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="nw",
            justify="left", wraplength=460,
        )
        self._body_lbl.grid(row=2, column=0, padx=24, pady=(12, 20), sticky="nw")

        # Step counter
        self._counter_lbl = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self._counter_lbl.grid(row=3, column=0, padx=24, pady=(0, 16), sticky="w")

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, pady=(0, 20), padx=28, sticky="ew")
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="Skip Tour", width=100, height=38,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_MUTED, border_width=1, border_color=BORDER_COLOR,
            corner_radius=8,
            command=self._finish,
        ).grid(row=0, column=0, sticky="w")

        self._back_btn = ctk.CTkButton(
            btn_row, text="← Back", width=100, height=38,
            fg_color=BG_SECONDARY, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self._prev,
        )
        self._back_btn.grid(row=0, column=2, padx=8)

        self._next_btn = ctk.CTkButton(
            btn_row, text="Next →", width=120, height=38,
            fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
            text_color="#1B1F24", corner_radius=8,
            command=self._next,
        )
        self._next_btn.grid(row=0, column=3)

    # ------------------------------------------------------------------

    def _show_step(self):
        step = _STEPS[self._step]
        self._title_lbl.configure(text=step["title"])
        self._body_lbl.configure(text=step["body"])
        self._counter_lbl.configure(
            text=f"Step {self._step + 1} of {len(_STEPS)}")

        # Dots
        for i, dot in enumerate(self._dots):
            dot.configure(
                fg_color=ACCENT_GOLD if i == self._step else BORDER_COLOR)

        # Buttons
        is_last = self._step == len(_STEPS) - 1
        self._next_btn.configure(
            text="Finish" if is_last else "Next →",
            fg_color=ACCENT_GREEN if is_last else ACCENT_GOLD,
        )
        self._back_btn.configure(state="normal" if self._step > 0 else "disabled")

        # Navigate app to relevant page
        if step["nav"] and self.navigate:
            try:
                self.navigate(step["nav"])
            except Exception:
                pass

    def _next(self):
        if self._step < len(_STEPS) - 1:
            self._step += 1
            self._show_step()
        else:
            self._finish()

    def _prev(self):
        if self._step > 0:
            self._step -= 1
            self._show_step()

    def _finish(self):
        if self.on_complete:
            self.on_complete()
        self.grab_release()
        self.destroy()
